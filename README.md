# LY-proj-Flask

# 🧠 Student AI Assistant

A Flask-based AI assistant that integrates with OpenAI's GPT models and stores data in MongoDB.

---

## 📁 Environment Setup

This project uses environment variables for sensitive configuration. Create a `.env` file in the root of the project directory with the following contents:

```env
# .env

FLASK_ENV=student-ai-assistant
MONGO_URI=your_uri
SECRET_KEY=studentassistant
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
UPLOAD_FOLDER=uploads
