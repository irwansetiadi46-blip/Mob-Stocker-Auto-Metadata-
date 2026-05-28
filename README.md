# Mob Stocker Metadata

AI-powered metadata generator for microstock photography. Built with Google Gemini AI.

## Features
- 🤖 AI-generated titles, descriptions, and keywords from images
- 📸 Support JPG, PNG, and EPS files
- 💉 XMP metadata injection for images
- 📄 Sidecar .xmp generation for EPS files
- 🔑 Support 50+ keywords for microstock
- 🎨 Modern, responsive UI

## Tech Stack
- Python Flask
- Google Gemini AI API
- Pillow (PIL)
- HTML/CSS/JavaScript

## Deployment on SnapDeploy

1. Push to GitHub
2. Import to SnapDeploy
3. Python runtime: 3.11
4. Start command: `python api/index.py`
5. Environment: `PORT=8080`

## Local Development

```bash
git clone https://github.com/yourusername/mob-stocker-metadata.git
cd mob-stocker-metadata
pip install -r requirements.txt
python api/index.py
