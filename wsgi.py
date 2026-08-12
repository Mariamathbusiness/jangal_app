from app import create_app

# C'est ce fichier que Render.com va exécuter
app = create_app()

if __name__ == "__main__":
    app.run()