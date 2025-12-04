// Project Leroy - Web App
// Vanilla JavaScript for lightweight, real-time visitation display

class VisitationApp {
    constructor() {
        this.visitations = [];
        this.refreshInterval = 60000; // 60 seconds
        this.carouselImages = [];
        this.carouselIndex = 0;
        this.carouselAutoplay = false;
        this.carouselAutoplayInterval = null;
        this.carouselAutoplayDelay = 5000; // 5 seconds per image
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadVisitations();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Modal close button
        document.querySelector('.close').addEventListener('click', () => {
            this.closeModal();
        });

        // Close modal on outside click
        document.getElementById('photo-modal').addEventListener('click', (e) => {
            if (e.target.id === 'photo-modal') {
                this.closeModal();
            }
        });

        // Carousel button
        document.getElementById('carousel-btn').addEventListener('click', () => {
            this.openCarousel();
        });

        // Carousel controls
        document.getElementById('carousel-close').addEventListener('click', () => {
            this.closeCarousel();
        });

        document.getElementById('carousel-prev').addEventListener('click', () => {
            this.carouselPrevious();
        });

        document.getElementById('carousel-next').addEventListener('click', () => {
            this.carouselNext();
        });

        document.getElementById('carousel-autoplay').addEventListener('click', () => {
            this.toggleCarouselAutoplay();
        });

        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.isCarouselOpen()) {
                    this.closeCarousel();
                } else {
                    this.closeModal();
                }
            }
            
            // Carousel navigation
            if (this.isCarouselOpen()) {
                if (e.key === 'ArrowLeft') {
                    this.carouselPrevious();
                } else if (e.key === 'ArrowRight') {
                    this.carouselNext();
                } else if (e.key === ' ') {
                    e.preventDefault();
                    this.toggleCarouselAutoplay();
                }
            }
        });
    }

    async loadVisitations() {
        try {
            const response = await fetch('/visitations.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.visitations = data;
            this.render();
            this.updateLastUpdate();
            
            // Update carousel if it's open
            if (this.isCarouselOpen()) {
                const currentImage = this.carouselImages[this.carouselIndex];
                this.carouselImages = this.getTodayImages();
                // Try to maintain current position
                if (currentImage) {
                    const newIndex = this.carouselImages.findIndex(img => img.src === currentImage.src);
                    if (newIndex >= 0) {
                        this.carouselIndex = newIndex;
                    }
                }
                this.updateCarouselImage();
            }
        } catch (error) {
            console.error('Error loading visitations:', error);
            this.showError(`Failed to load visitations: ${error.message}`);
        }
    }

    render() {
        const container = document.getElementById('visitations');
        const loading = document.getElementById('loading');
        const error = document.getElementById('error');

        // Hide loading and error
        loading.style.display = 'none';
        error.style.display = 'none';

        if (this.visitations.length === 0) {
            container.innerHTML = '<div class="loading">No visitations yet. Waiting for birds...</div>';
            return;
        }

        // Update count
        document.getElementById('visitation-count').textContent = 
            `${this.visitations.length} ${this.visitations.length === 1 ? 'visitation' : 'visitations'}`;

        // Render cards
        container.innerHTML = this.visitations.map((visit, index) => this.renderCard(visit, index)).join('');
        
        // Attach click handlers
        this.visitations.forEach((visit, index) => {
            const card = container.children[index];
            if (card) {
                card.addEventListener('click', () => this.openModal(visit));
            }
        });
    }

    renderCard(visit, index) {
        // Get primary species (first in species_observations or fallback to species)
        const primarySpecies = visit.species_observations?.[0] || {
            common_name: visit.species || 'Unknown',
            scientific_name: 'Unknown',
            count: visit.records?.length || 0
        };

        const speciesCount = visit.species_count || 1;
        const hasMultipleSpecies = speciesCount > 1;

        return `
            <div class="visitation-card" data-visitation-id="${visit.visitation_id}">
                <img src="${visit.best_photo}" alt="${primarySpecies.common_name}" class="card-image" 
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27200%27 height=%27200%27%3E%3Crect fill=%27%23ddd%27 width=%27200%27 height=%27200%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 text-anchor=%27middle%27 dy=%27.3em%27 fill=%27%23999%27%3ENo Image%3C/text%3E%3C/svg%3E'">
                <div class="card-content">
                    <div class="card-header">
                        <div>
                            <div class="card-title">${this.escapeHtml(primarySpecies.common_name)}</div>
                            <div class="scientific-name">${this.escapeHtml(primarySpecies.scientific_name)}</div>
                        </div>
                        ${hasMultipleSpecies ? `<span class="species-count-badge">${speciesCount} species</span>` : ''}
                    </div>
                    
                    ${hasMultipleSpecies ? this.renderMultiSpeciesList(visit.species_observations) : ''}
                    
                    <div class="card-meta">
                        <span>${this.formatDate(visit.start_datetime || visit.datetime)}</span>
                        <span>${this.formatDuration(visit.duration)}</span>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="event.stopPropagation(); app.openModalByIndex(${index})">
                        View Photos
                    </button>
                </div>
            </div>
        `;
    }

    renderMultiSpeciesList(speciesObservations) {
        if (!speciesObservations || speciesObservations.length <= 1) return '';

        return `
            <div class="multi-species-list">
                <h4>All Species in This Visitation</h4>
                ${speciesObservations.map(obs => `
                    <div class="species-item">
                        <div>
                            <div class="species-item-name">${this.escapeHtml(obs.common_name)}</div>
                            <div class="scientific-name" style="font-size: 0.8rem; margin-top: 0.1rem;">
                                ${this.escapeHtml(obs.scientific_name)}
                            </div>
                        </div>
                        <div class="species-item-count">${obs.count} photos</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    openModalByIndex(index) {
        if (index >= 0 && index < this.visitations.length) {
            this.openModal(this.visitations[index]);
        }
    }

    openModal(visit) {
        const modal = document.getElementById('photo-modal');
        const modalBody = document.getElementById('modal-body');

        // Get primary species info
        const primarySpecies = visit.species_observations?.[0] || {
            common_name: visit.species || 'Unknown',
            scientific_name: 'Unknown'
        };

        modalBody.innerHTML = `
            <div class="modal-header">
                <div class="modal-title">${this.escapeHtml(primarySpecies.common_name)}</div>
                <div class="modal-subtitle">
                    ${this.escapeHtml(primarySpecies.scientific_name)} • 
                    ${this.formatDate(visit.start_datetime || visit.datetime)} • 
                    Duration: ${this.formatDuration(visit.duration)}
                </div>
            </div>

            ${visit.full_image ? `
                <div class="photo-item best-photo">
                    <img src="${visit.full_image}" alt="Full scene">
                </div>
            ` : ''}

            ${visit.species_observations && visit.species_observations.length > 1 ? `
                <div class="species-section">
                    <h3>All Species (${visit.species_count})</h3>
                    ${visit.species_observations.map(obs => `
                        <div style="margin-bottom: 1.5rem;">
                            <h4 style="margin-bottom: 0.5rem;">
                                ${this.escapeHtml(obs.common_name)} 
                                <span style="font-weight: normal; color: #7f8c8d; font-size: 0.9rem;">
                                    (${this.escapeHtml(obs.scientific_name)})
                                </span>
                            </h4>
                            <div class="photo-gallery">
                                ${obs.photos.map(photo => `
                                    <div class="photo-item ${photo.is_best ? 'best-photo' : ''}">
                                        <img src="${photo.filename}" alt="${obs.common_name}" 
                                             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27200%27 height=%27200%27%3E%3Crect fill=%27%23ddd%27 width=%27200%27 height=%27200%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 text-anchor=%27middle%27 dy=%27.3em%27 fill=%27%23999%27%3ENo Image%3C/text%3E%3C/svg%3E'">
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            <div class="photo-gallery">
                ${(visit.records || []).map((record, index) => `
                    <div class="photo-item ${record.filename === visit.best_photo ? 'best-photo' : ''}">
                        <img src="${record.filename}" alt="${record.species || 'Bird'}" 
                             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27200%27 height=%27200%27%3E%3Crect fill=%27%23ddd%27 width=%27200%27 height=%27200%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 text-anchor=%27middle%27 dy=%27.3em%27 fill=%27%23999%27%3ENo Image%3C/text%3E%3C/svg%3E'">
                    </div>
                `).join('')}
            </div>
        `;

        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        const modal = document.getElementById('photo-modal');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    showError(message) {
        const error = document.getElementById('error');
        const loading = document.getElementById('loading');
        error.textContent = message;
        error.style.display = 'block';
        loading.style.display = 'none';
    }

    updateLastUpdate() {
        const now = new Date();
        document.getElementById('last-update').textContent = 
            `Last updated: ${now.toLocaleTimeString()}`;
    }

    startAutoRefresh() {
        setInterval(() => {
            this.loadVisitations();
        }, this.refreshInterval);
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    formatDuration(seconds) {
        if (!seconds) return '';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        if (mins > 0) {
            return `${mins}m ${secs}s`;
        }
        return `${secs}s`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Carousel functions
    getTodayImages() {
        const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
        const images = [];

        this.visitations.forEach(visit => {
            const visitDate = (visit.start_datetime || visit.datetime).split(' ')[0];
            
            // Only include visitations from today
            if (visitDate === today) {
                // Add all photos from species observations
                if (visit.species_observations) {
                    visit.species_observations.forEach(obs => {
                        obs.photos.forEach(photo => {
                            images.push({
                                src: photo.filename,
                                species: obs.common_name,
                                scientific: obs.scientific_name,
                                datetime: photo.datetime,
                                detection_score: photo.detection_score,
                                classification_score: photo.classification_score
                            });
                        });
                    });
                }
                
                // Also add records if available
                if (visit.records) {
                    visit.records.forEach(record => {
                        // Avoid duplicates (photos might be in both places)
                        if (!images.find(img => img.src === record.filename)) {
                            images.push({
                                src: record.filename,
                                species: record.species || visit.species || 'Unknown',
                                scientific: 'Unknown',
                                datetime: record.datetime,
                                detection_score: record.detection_score,
                                classification_score: record.classification_score
                            });
                        }
                    });
                }
            }
        });

        return images;
    }

    openCarousel() {
        this.carouselImages = this.getTodayImages();
        
        if (this.carouselImages.length === 0) {
            alert('No images from today yet. Check back later!');
            return;
        }

        this.carouselIndex = 0;
        const carousel = document.getElementById('carousel');
        carousel.style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        this.updateCarouselImage();
        this.startCarouselAutoplay();
    }

    closeCarousel() {
        const carousel = document.getElementById('carousel');
        carousel.style.display = 'none';
        document.body.style.overflow = 'auto';
        this.stopCarouselAutoplay();
    }

    isCarouselOpen() {
        const carousel = document.getElementById('carousel');
        return carousel.style.display === 'block';
    }

    updateCarouselImage() {
        if (this.carouselImages.length === 0) return;

        const image = this.carouselImages[this.carouselIndex];
        const imgElement = document.getElementById('carousel-image');
        const speciesElement = document.getElementById('carousel-species');
        const metaElement = document.getElementById('carousel-meta');
        const counterElement = document.getElementById('carousel-counter');

        imgElement.src = image.src;
        imgElement.alt = image.species;
        
        speciesElement.innerHTML = `
            <div>${this.escapeHtml(image.species)}</div>
            <div style="font-size: 0.9rem; font-style: italic; opacity: 0.8; margin-top: 0.25rem;">
                ${this.escapeHtml(image.scientific)}
            </div>
        `;
        
        const date = new Date(image.datetime);
        metaElement.textContent = `
            ${date.toLocaleString()} • 
            Detection: ${image.detection_score}% • 
            Classification: ${image.classification_score}%
        `;
        
        counterElement.textContent = `${this.carouselIndex + 1} / ${this.carouselImages.length}`;
    }

    carouselNext() {
        this.carouselIndex = (this.carouselIndex + 1) % this.carouselImages.length;
        this.updateCarouselImage();
        this.resetCarouselAutoplay();
    }

    carouselPrevious() {
        this.carouselIndex = (this.carouselIndex - 1 + this.carouselImages.length) % this.carouselImages.length;
        this.updateCarouselImage();
        this.resetCarouselAutoplay();
    }

    startCarouselAutoplay() {
        this.carouselAutoplay = true;
        this.updateCarouselAutoplayButton();
        this.resetCarouselAutoplay();
    }

    stopCarouselAutoplay() {
        this.carouselAutoplay = false;
        if (this.carouselAutoplayInterval) {
            clearInterval(this.carouselAutoplayInterval);
            this.carouselAutoplayInterval = null;
        }
        this.updateCarouselAutoplayButton();
    }

    toggleCarouselAutoplay() {
        if (this.carouselAutoplay) {
            this.stopCarouselAutoplay();
        } else {
            this.startCarouselAutoplay();
        }
    }

    resetCarouselAutoplay() {
        if (this.carouselAutoplayInterval) {
            clearInterval(this.carouselAutoplayInterval);
        }
        
        if (this.carouselAutoplay) {
            this.carouselAutoplayInterval = setInterval(() => {
                this.carouselNext();
            }, this.carouselAutoplayDelay);
        }
    }

    updateCarouselAutoplayButton() {
        const btn = document.getElementById('carousel-autoplay');
        if (this.carouselAutoplay) {
            btn.textContent = '⏸️ Pause';
            btn.classList.remove('paused');
            btn.classList.add('playing');
        } else {
            btn.textContent = '▶️ Play';
            btn.classList.remove('playing');
            btn.classList.add('paused');
        }
    }
}

// Initialize app
const app = new VisitationApp();

