#!/usr/bin/env python3
"""
Bluesky (atproto) Social Media Posting Module for Project Leroy
Optional posting - only posts if authenticated, otherwise silently ignores
"""
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import atproto (Bluesky SDK)
try:
    from atproto import Client, models
    ATPROTO_AVAILABLE = True
except ImportError:
    ATPROTO_AVAILABLE = False
    logger.warning("atproto library not available. Install with: pip install atproto")


class BlueskyPoster:
    """
    Handles posting to Bluesky with frequency regulation and error handling.
    Only posts if authenticated, otherwise silently ignores.
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.authenticated = False
        self.enabled = os.getenv('BLUESKY_ENABLED', 'false').lower() == 'true'
        self.handle = os.getenv('BLUESKY_HANDLE', '')
        self.app_password = os.getenv('BLUESKY_APP_PASSWORD', '')
        
        # Posting rules
        self.max_posts_per_day = 1  # Single daily summary
        self.posting_window_start = 19  # 7:00 PM (evening)
        self.posting_window_end = 21   # 9:00 PM
        
        # Track posting history
        self.post_history_file = 'storage/bluesky_post_history.json'
        self.post_history = self._load_post_history()
        
        # Initialize if enabled
        if self.enabled and ATPROTO_AVAILABLE:
            self._authenticate()
        elif self.enabled and not ATPROTO_AVAILABLE:
            logger.warning("Bluesky posting enabled but atproto library not installed. Install with: pip install atproto")
    
    def _load_post_history(self) -> List[Dict]:
        """Load posting history from file."""
        if os.path.exists(self.post_history_file):
            try:
                import json
                with open(self.post_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load post history: {e}")
        return []
    
    def _save_post_history(self):
        """Save posting history to file."""
        try:
            import json
            os.makedirs(os.path.dirname(self.post_history_file), exist_ok=True)
            with open(self.post_history_file, 'w') as f:
                json.dump(self.post_history, f, default=str)
        except Exception as e:
            logger.error(f"Failed to save post history: {e}")
    
    def _authenticate(self) -> bool:
        """Authenticate with Bluesky."""
        if not ATPROTO_AVAILABLE:
            logger.warning("atproto library not available. Cannot authenticate.")
            return False
        
        if not self.handle or not self.app_password:
            logger.warning("Bluesky credentials not configured. Set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD.")
            return False
        
        try:
            self.client = Client()
            self.client.login(login=self.handle, password=self.app_password)
            self.authenticated = True
            logger.info("Successfully authenticated with Bluesky")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Bluesky: {e}")
            self.authenticated = False
            return False
    
    def _can_post(self) -> bool:
        """
        Check if posting is allowed based on frequency and time rules.
        
        Returns:
            True if posting is allowed, False otherwise
        """
        if not self.enabled or not self.authenticated:
            return False
        
        now = datetime.now()
        current_hour = now.hour
        
        # Check posting window
        if current_hour < self.posting_window_start or current_hour >= self.posting_window_end:
            logger.debug(f"Outside posting window ({self.posting_window_start}:00 - {self.posting_window_end}:00)")
            return False
        
        # Check posts today
        today = now.date()
        posts_today = [
            p for p in self.post_history
            if datetime.fromisoformat(p['timestamp']).date() == today
        ]
        
        if len(posts_today) >= self.max_posts_per_day:
            logger.debug(f"Maximum posts per day ({self.max_posts_per_day}) reached")
            return False
        
        # Check if already posted today (only 1 post per day)
        if posts_today:
            logger.debug("Already posted today (1 post per day maximum)")
            return False
        
        return True
    
    def post_text(self, text: str) -> bool:
        """
        Post text-only post to Bluesky.
        
        Args:
            text: Post text content
            
        Returns:
            True if posted successfully, False otherwise
        """
        if not self._can_post():
            return False
        
        if not self.client or not self.authenticated:
            logger.debug("Not authenticated with Bluesky, skipping post")
            return False
        
        try:
            # Create post using atproto API
            # Note: API may vary by atproto version - adjust if needed
            post_record = models.AppBskyFeedPost.Main(
                text=text,
                created_at=datetime.now().isoformat()
            )
            
            self.client.com.atproto.repo.create_record(
                models.ComAtprotoRepoCreateRecord.Data(
                    repo=self.client.me.did,
                    collection=models.ids.AppBskyFeedPost,
                    record=post_record
                )
            )
            
            # Record in history
            self.post_history.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'text',
                'text': text[:100]  # Store preview
            })
            self._save_post_history()
            
            logger.info(f"Posted to Bluesky: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post to Bluesky: {e}")
            return False
    
    def post_with_image(self, text: str, image_path: str) -> bool:
        """
        Post with image to Bluesky.
        
        Args:
            text: Post text content
            image_path: Path to image file
            
        Returns:
            True if posted successfully, False otherwise
        """
        if not self._can_post():
            return False
        
        if not self.client or not self.authenticated:
            logger.debug("Not authenticated with Bluesky, skipping post")
            return False
        
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return False
        
        try:
            # Read and upload image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Upload image blob
            upload = self.client.com.atproto.repo.upload_blob(image_data)
            
            # Create post with image embed
            embed = models.AppBskyEmbedImages.Main(
                images=[
                    models.AppBskyEmbedImages.Image(
                        image=upload.blob,
                        alt=text[:200]  # Alt text
                    )
                ]
            )
            
            # Create post with image embed
            # Note: API may vary by atproto version - adjust if needed
            if hasattr(self.client, 'send_post'):
                # Simple API
                self.client.send_post(text=text, embed=embed)
            else:
                # Advanced API
                post_record = models.AppBskyFeedPost.Main(
                    text=text,
                    embed=embed,
                    created_at=datetime.now().isoformat()
                )
                self.client.com.atproto.repo.create_record(
                    models.ComAtprotoRepoCreateRecord.Data(
                        repo=self.client.me.did,
                        collection=models.ids.AppBskyFeedPost,
                        record=post_record
                    )
                )
            
            # Record in history
            self.post_history.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'image',
                'text': text[:100],
                'image_path': image_path
            })
            self._save_post_history()
            
            logger.info(f"Posted to Bluesky with image: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post to Bluesky with image: {e}")
            return False
    
    def select_best_photos(self, visitations: List[Dict], count: int = 5) -> List[Dict]:
        """
        Select best photos with species diversity and high clarity.
        
        Args:
            visitations: List of visitation dictionaries
            count: Number of photos to select (default: 5)
            
        Returns:
            List of photo dictionaries with path, species, clarity, confidence
        """
        import cv2
        
        all_photos = []
        
        for visit in visitations:
            records = visit.get('records', [])
            for record in records:
                if 'full' in record.get('filename', ''):
                    continue  # Skip full images, prefer boxed
                
                filename = record.get('filename', '')
                if not filename:
                    continue
                
                # Calculate clarity score
                full_path = os.path.join('/var/www/html', filename.lstrip('/'))
                clarity_score = 0
                if os.path.exists(full_path):
                    try:
                        image = cv2.imread(full_path)
                        if image is not None:
                            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                            clarity_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                    except Exception:
                        pass
                
                # Get species
                species = record.get('species', 'Unknown')
                detection_score = int(record.get('detection_score', 0))
                classification_score = int(record.get('classification_score', 0))
                total_score = detection_score + classification_score + clarity_score
                
                all_photos.append({
                    'filename': filename,
                    'full_path': full_path,
                    'species': species,
                    'clarity_score': clarity_score,
                    'detection_score': detection_score,
                    'classification_score': classification_score,
                    'total_score': total_score,
                    'datetime': record.get('datetime', '')
                })
        
        # Sort by total score (clarity + detection + classification)
        all_photos.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Select top photos ensuring species diversity
        selected = []
        species_seen = set()
        
        # First pass: Get best photo per species
        for photo in all_photos:
            if len(selected) >= count:
                break
            species = photo['species']
            if species not in species_seen:
                selected.append(photo)
                species_seen.add(species)
        
        # Second pass: Fill remaining slots with highest scores
        for photo in all_photos:
            if len(selected) >= count:
                break
            if photo not in selected:
                selected.append(photo)
        
        # Sort selected by score for final order
        selected.sort(key=lambda x: x['total_score'], reverse=True)
        
        return selected[:count]
    
    def get_daily_summary(self, visitations: List[Dict]) -> str:
        """
        Generate daily summary text from visitations.
        
        Args:
            visitations: List of visitation dictionaries
            
        Returns:
            Formatted summary text
        """
        if not visitations:
            return "No visitations today."
        
        # Count species
        species_counts = {}
        for visit in visitations:
            # Support both old format (single species) and new format (species_observations)
            if 'species_observations' in visit:
                for obs in visit['species_observations']:
                    species = obs['common_name']
                    species_counts[species] = species_counts.get(species, 0) + obs['count']
            else:
                species = visit.get('species', 'Unknown')
                species_counts[species] = species_counts.get(species, 0) + 1
        
        # Build summary
        total_visits = len(visitations)
        species_count = len(species_counts)
        
        summary = f"Today I was visited {total_visits} time{'s' if total_visits != 1 else ''}"
        if species_count > 1:
            summary += f" by {species_count} different species:\n"
            for species, count in sorted(species_counts.items(), key=lambda x: x[1], reverse=True):
                summary += f"- {count} {species}\n"
        else:
            species_name = list(species_counts.keys())[0] if species_counts else "birds"
            summary += f" by {species_name}.\n"
        
        return summary.strip()
    
    def post_daily_summary(self, visitations: List[Dict]) -> bool:
        """
        Post daily summary with 5 best photos (varying species, high clarity).
        
        Args:
            visitations: List of visitation dictionaries
            
        Returns:
            True if posted successfully, False otherwise
        """
        summary_text = self.get_daily_summary(visitations)
        
        # Select 5 best photos with species diversity
        best_photos = self.select_best_photos(visitations, count=5)
        
        if best_photos:
            # Post with multiple images (Bluesky supports up to 4 images per post)
            # We'll use top 4 to stay within limits
            photo_paths = [p['full_path'] for p in best_photos[:4] if os.path.exists(p['full_path'])]
            
            if photo_paths:
                summary_text += "\n\nHighlights:"
                return self.post_with_multiple_images(summary_text, photo_paths)
            else:
                # Fallback to text if no valid photos
                return self.post_text(summary_text)
        else:
            return self.post_text(summary_text)
    
    def post_with_multiple_images(self, text: str, image_paths: List[str]) -> bool:
        """
        Post with multiple images (up to 4 for Bluesky).
        
        Args:
            text: Post text content
            image_paths: List of image file paths (max 4)
            
        Returns:
            True if posted successfully, False otherwise
        """
        if not self._can_post():
            return False
        
        if not self.client or not self.authenticated:
            logger.debug("Not authenticated with Bluesky, skipping post")
            return False
        
        if not image_paths:
            return self.post_text(text)
        
        # Limit to 4 images (Bluesky limit)
        image_paths = image_paths[:4]
        
        try:
            images = []
            for image_path in image_paths:
                if not os.path.exists(image_path):
                    continue
                
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                # Upload image blob
                upload = self.client.com.atproto.repo.upload_blob(image_data)
                
                images.append(
                    models.AppBskyEmbedImages.Image(
                        image=upload.blob,
                        alt=os.path.basename(image_path)
                    )
                )
            
            if not images:
                return self.post_text(text)
            
            # Create post with multiple images
            embed = models.AppBskyEmbedImages.Main(images=images)
            
            post_record = models.AppBskyFeedPost.Main(
                text=text,
                embed=embed,
                created_at=datetime.now().isoformat()
            )
            
            self.client.com.atproto.repo.create_record(
                models.ComAtprotoRepoCreateRecord.Data(
                    repo=self.client.me.did,
                    collection=models.ids.AppBskyFeedPost,
                    record=post_record
                )
            )
            
            # Record in history
            self.post_history.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'multi_image',
                'text': text[:100],
                'image_count': len(images)
            })
            self._save_post_history()
            
            logger.info(f"Posted to Bluesky with {len(images)} images: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post to Bluesky with images: {e}")
            # Fallback to text-only post
            return self.post_text(text)
    
    def post_visitation(self, visitation: Dict, photo_path: Optional[str] = None) -> bool:
        """
        Post individual visitation (for special visitations).
        
        Args:
            visitation: Visitation dictionary
            photo_path: Optional path to best photo
            
        Returns:
            True if posted successfully, False otherwise
        """
        # Only post special visitations
        # Criteria: high confidence, multiple species, or rare species
        
        confidence = 0
        species_count = 1
        
        if 'species_observations' in visitation:
            species_count = len(visitation['species_observations'])
            # Get highest confidence
            confidences = [obs.get('confidence', 0) for obs in visitation['species_observations']]
            confidence = max(confidences) if confidences else 0
        else:
            # Old format - check records
            records = visitation.get('records', [])
            if records:
                scores = [int(r.get('classification_score', 0)) for r in records]
                confidence = max(scores) / 100.0 if scores else 0
        
        # Post if: high confidence (>85%) OR multiple species (3+)
        if confidence < 0.85 and species_count < 3:
            logger.debug(f"Skipping visitation post: confidence={confidence:.2f}, species_count={species_count}")
            return False
        
        # Build post text
        if species_count > 1:
            text = f"Multiple species visited together! ({species_count} species)"
        else:
            species = visitation.get('species', 'Unknown')
            text = f"Special visitor: {species}"
        
        if photo_path:
            return self.post_with_image(text, photo_path)
        else:
            return self.post_text(text)

