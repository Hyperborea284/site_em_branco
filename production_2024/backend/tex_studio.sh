#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <caminho_para_arquivo_tex>"
    exit 1
fi

tex_file="$1"
tex_directory=$(dirname "$tex_file")
output_directory="pdf_output/"
file_base=$(basename "$tex_file" .tex)

cd "$tex_directory"

tex_file=$(echo "$tex_file" | sed 's|pdf_output/||')

texstudio "$tex_file" &

sleep 4
xdotool key F5
sleep 10
xdotool key Ctrl+w
sleep 1
xdotool key Ctrl+q

cd ..

okular "${output_directory}${file_base}.pdf" &

find "${output_directory}" -type f ! \( -name "*.pdf" -o -name "*.tex" -o -name "*.bib" -o -name "*.db" -o -name "*.txt" -o -name "*.png" \) -exec rm {} +
