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
  echo "inkscape -z -f $abs -e $abspng -d 300 -C -b white"
  inkscape -z -f "$abs" -e "$abspng" -d 300 -C -b white
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
    for i in "${1}/"*.svg; do
        [ -f "$i" ] || break
        convertSvgPng "$i"
        convertPngJpg "$abspng"
    done
else
    echo "Argument error, please give path to your folder containing svg files as the only argument."
fi
