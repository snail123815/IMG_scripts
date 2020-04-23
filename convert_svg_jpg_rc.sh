getAbsFilePath() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

convertSvgPng() {
  # $1 : absolute filepath
  # inkscape seems to take only absolute path
  local abs=$(getAbsFilePath "$1")
  abspng="${abs%.*}.png"
  echo
  echo "==============================================================="
  echo
  echo "/Users/durand.dc/Applications/Inkscape_rc.app/Contents/MacOS/inkscape -o $abspng -d 300 -C -b white -y 1 $abs "
  /Users/durand.dc/Applications/Inkscape_rc.app/Contents/MacOS/inkscape -o "$abspng" -d 300 -C -b white -y 1 "$abs" 
}

convertPngJpg() {
  # $1 : absolute filepath
  echo
  echo "--------------------------------"
  echo
  echo "magick $1 -quality 50 "${1%.*}.jpg""
  magick "$1" -quality 50 "${1%.*}.jpg"
  rm "$1"
}

if [ $# -eq 1 ]; then
    convertSvgPng "$1"
    convertPngJpg "$abspng"
else
    echo "Argument error, please give path to your svg file as the only argument."
fi
