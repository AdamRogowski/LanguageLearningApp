# Language Learning App

A Django-based progressive web application designed to help users learn foreign languages through interactive vocabulary practice sessions. The app supports collaborative lesson creation, personalized progress tracking, and adaptive learning algorithms.

## ✨ Features

- **📚 Lesson Management**: Create, edit, import/export lessons with vocabulary words
- **🎯 Interactive Practice**: Adaptive practice sessions with multiple modes (spelling, pronunciation)
- **📊 Progress Tracking**: Individual progress monitoring per word and lesson
- **🤝 Collaboration**: Share lessons with configurable access control (private/read-only/writable)
- **🔧 Smart Feedback**: Levenshtein distance-based answer evaluation with customizable error margins
- **🎵 Audio Support**: Text-to-speech integration for pronunciation practice
- **📱 PWA Ready**: Progressive Web App with offline capabilities
- **👥 User Management**: Secure authentication with profile customization
- **⭐ Rating System**: Community-driven lesson ratings and reviews

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/AdamRogowski/LanguageLearningApp.git
   cd LanguageLearningApp
   ```

2. **Set up virtual environment**

   ```bash
   python -m venv _env
   source _env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the database**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # Optional: create admin user
   ```

5. **Run the development server**

   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:8000`

## 🏗️ Architecture

The application follows Django's MVT (Model-View-Template) architecture:

- **Models**: User profiles, lessons, words, progress tracking, ratings
- **Views**: Business logic for lesson management, practice sessions, user authentication
- **Templates**: Responsive HTML templates with PWA capabilities
- **Database**: SQLite (development) / PostgreSQL (production ready)

## 🧪 Testing

Run the comprehensive test suite using pytest:

```bash
pytest
```

The project includes 39+ automated tests covering authentication, lesson management, practice sessions, and access control.

## 📖 Usage

1. **Register/Login** to access personalized features
2. **Browse Repository** to discover public lessons
3. **Import Lessons** to your personal workspace
4. **Create Custom Lessons** with your vocabulary
5. **Practice** with adaptive sessions that adjust to your progress
6. **Track Progress** and review your learning statistics

## 🐳 Docker Support

```bash
docker build -t language-learning-app .
docker run -p 8000:8000 language-learning-app
```

## 🙏 Acknowledgments

- Built with [Django](https://djangoproject.com/)
- Powered by Python
- Text-to-speech integration
- Progressive Web App technologies

---

**Happy Learning! 🎓**
