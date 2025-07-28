#!/bin/bash

echo "Создаю структуру папок и CSS..."

mkdir -p src dist

cat > src/input.css <<EOF
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

echo "Запускаю tailwindcss watch для генерации CSS..."

npx tailwindcss -i ./src/input.css -o ./dist/output.css --watch
