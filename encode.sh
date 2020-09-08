for i in storage/video/*.mp4;
  do name=`echo "$i" | cut -d'.' -f1`
  echo "name $name"
  ffmpeg -i "$i" -c:v libx264 -preset medium -crf 22 -c:a copy "${name}.mkv"
done
cp -R storage/video/*.mkv storage/video/encoded