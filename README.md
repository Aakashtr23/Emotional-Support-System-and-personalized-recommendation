# 🧠 Emotional Support System with Personalized Recommendations 🎤

This project is an AI-powered **Emotional Support System** that detects **emotions from speech** and provides **personalized recommendations** to support mental health and well-being.  

It works by converting **audio (speech) → text → emotion detection → personalized response**, creating an empathy-driven assistant.

---

## 📌 About the Project
- Users speak into the system using a **microphone**.  
- The system performs **Speech-to-Text conversion** (ASR - Automatic Speech Recognition).  
- The **Emotion Detection Model** analyzes the transcript and audio features to classify emotions (*happy, sad, angry, neutral, etc.*).  
- A **Recommendation Engine** provides **personalized suggestions** such as:
  - 🎵 Music playlists
  - 🧘 Relaxation techniques
  - 📚 Motivational content
  - ✅ Productivity tips  

This system can be used for **mental health support, personal wellness tracking, and smart virtual assistants**.

---

## 🚀 Features
- 🎤 **Audio to Text** – Converts user’s speech into text.  
- 😊 **Emotion Detection** – Detects emotions using text + acoustic features.  
- 🎯 **Personalized Recommendations** – Suggests activities/resources tailored to user’s emotional state.  
- 💬 **Supportive Feedback** – Provides empathy-driven responses.  
- 📊 **Emotion Insights** – Can be extended to track user’s emotional trends over time.  

---

## 🛠️ Tech Stack
- **Programming**: Python  
- **Speech Recognition**: Whisper / Vosk / Google Speech API  
- **Emotion Detection**: Machine Learning (SVM, LSTM, CNN, or transformer models)  
- **Libraries**: Librosa, TensorFlow/PyTorch, Scikit-learn, NumPy, Pandas  
- **Backend**: Flask / FastAPI  
- **Frontend (optional)**: React.js or HTML/CSS  
- **Database**: MongoDB / MySQL (for user data & history)  

---

## 📂 Workflow
1. 🎤 **Audio Input** → User speaks into mic  
2. 📝 **Speech-to-Text** → Convert audio into transcript  
3. 😊 **Emotion Detection** → Classify emotional state  
4. 🎯 **Recommendation System** → Suggest personalized activities/resources  
5. 💬 **Supportive Response** → Provide empathetic feedback  

---

## ⚡ Installation & Setup
```bash
# Clone repository
git clone https://github.com/Aakashtr23/Emotional-Support-System-and-personalized-recommendation.git

# Navigate to project folder
cd Emotional-Support-System-and-personalized-recommendation

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
