# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
from flask import Flask, render_template, request, jsonify
import os
import speech_recognition as sr
from datetime import datetime
from pydub import AudioSegment # Added for audio conversion
import traceback          
import googletrans

print(googletrans.LANGUAGES)
from googletrans import Translator

translator = Translator()
result = translator.translate('how are you', src='en', dest='hi')

print(result.src)
print(result.dest)
print(result.text)
app = Flask(__name__)


UPLOAD_FOLDER = 'uploads'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def home():
    
    return render_template('index.html')

# Define the route for handling audio uploads, restricted to POST method
@app.route('/upload', methods=['POST'])
def upload():
    """
    Handles audio file uploads, converts to WAV (if needed), performs
    speech-to-text transcription using the specified language, saves the
    original audio, converted WAV, and transcript details to files,
    and prints ONLY the final transcription result or status/error message
    to the console where the Flask server is running.
    """
    # Initialize variables to store results and paths
    server_transcript = "[Transcription not attempted]"
    wav_path = None
    original_audio_path = None
    user_transcript = '[User transcript not available]' # From frontend form
    language_code = 'en-IN' # Default language if not provided by frontend
    language_used = language_code # Track the language code actually used for transcription

    try:
        # --- 1. Get Uploaded Data (Audio File and Form Data) ---
        audio_file = request.files.get('audio')
        user_transcript = request.form.get('transcript', '[User transcript not provided]')
        # Get the desired language code from the form data sent by the frontend
        language_code = request.form.get('language', 'en-IN') # Use default if not sent
        language_used = language_code # Store the requested language
        print('language_used',language_used)
        # --- Basic Validation ---
        if not audio_file:
            # Optional: Log critical failures to console
            # print("Error: No audio file received in the request.", flush=True)
            return jsonify({"message": "No audio file received in the request."}), 400

        if not audio_file.filename:
             # Optional: Log critical failures to console
             # print("Error: Audio file received but has no filename.", flush=True)
             return jsonify({"message": "Audio file has no filename."}), 400

        # --- 2. Prepare File Paths (using timestamp for uniqueness) ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = audio_file.filename
        original_extension = os.path.splitext(original_filename)[1]

        # Handle cases where the browser might not send an extension but sends mime type
        if not original_extension:
            mime_type = audio_file.content_type
            if mime_type == 'audio/webm': original_extension = '.webm'
            elif mime_type == 'audio/ogg': original_extension = '.ogg'
            elif mime_type == 'audio/wav': original_extension = '.wav'
            elif mime_type == 'audio/mp4': original_extension = '.mp4' # Common case
            elif mime_type == 'audio/aac': original_extension = '.aac' # Common case
            elif mime_type == 'audio/mpeg': original_extension = '.mp3' # Common case
            else: original_extension = '.bin' # Fallback
            # print(f"Warning: No file extension found, determined '{original_extension}' from mime type '{mime_type}'.", flush=True) # Removed

        # Construct full paths for saving files
        original_audio_path = os.path.join(UPLOAD_FOLDER, f"audio_{timestamp}{original_extension}")
        wav_path = os.path.join(UPLOAD_FOLDER, f"audio_{timestamp}.wav")
        # Include language code in the transcript filename for clarity
        transcript_path = os.path.join(UPLOAD_FOLDER, f"transcript_{timestamp}_{language_code}.txt")

        # --- 3. Save Original Uploaded Audio File ---
        # print(f"Saving original audio to: {original_audio_path}", flush=True) # Removed
        audio_file.save(original_audio_path)
        # print("Original audio saved successfully.", flush=True) # Removed

        # --- 4. Convert Audio to WAV using pydub (if not already WAV) ---
        # SpeechRecognition library typically works best with WAV files
        if original_extension.lower() != '.wav':
            try:
                # print(f"Attempting to convert '{original_audio_path}' to WAV format at '{wav_path}'...", flush=True) # Removed
                # Load the audio file using pydub (handles various formats)
                audio_segment = AudioSegment.from_file(original_audio_path)
                # Export the audio segment as a WAV file
                audio_segment.export(wav_path, format="wav")
                # print("Conversion to WAV successful.", flush=True) # Removed
            except Exception as convert_err:
                # Log conversion errors if needed for debugging
                # print(f"Error during audio conversion: {convert_err}", flush=True)
                # print(traceback.format_exc(), flush=True) # Uncomment for detailed traceback
                server_transcript = "[Audio conversion failed, transcription skipped]"
                # *** Print the status here if conversion fails ***
                print(f"--> FINAL STATUS ({language_used}): {server_transcript}", flush=True)
                # Optionally clean up the failed original file if needed
                # if os.path.exists(original_audio_path): os.remove(original_audio_path)
                # Return an error response to the client
                return jsonify({
                    "message": "Error converting audio file to WAV.",
                    "error": str(convert_err),
                    "user_transcript": user_transcript,
                    "server_transcript": server_transcript,
                    "language_used": language_used
                }), 500 # Internal Server Error status
        else:
             # If the uploaded file is already WAV, just use its path
             # print("Uploaded file is already WAV. Skipping conversion.", flush=True) # Removed
             wav_path = original_audio_path # Use the original path directly

        # --- 5. Transcribe the Converted WAV File using SpeechRecognition ---
        # print(f"Attempting transcription on WAV file: {wav_path} using language: {language_code}", flush=True) # Removed
        recognizer = sr.Recognizer()
        try:
            # Use the WAV file as the audio source
            with sr.AudioFile(wav_path) as source:
                # print("Reading audio data from file...", flush=True) # Removed
                # Record the audio data from the file
                audio_data = recognizer.record(source)
                # print("Audio data read successfully.", flush=True) # Removed

            # Perform speech recognition using Google Web Speech API
            # print(f"Sending audio data to Google Speech Recognition (using {language_code})...", flush=True) # Removed
            server_transcript = recognizer.recognize_google(audio_data, language=language_code)
            # Note: No print statement here; the final one is after the except blocks

        # Handle common SpeechRecognition errors
        except sr.UnknownValueError:
            # Google Speech Recognition couldn't understand the audio
            # print(f"Google Speech Recognition ({language_code}) could not understand audio.", flush=True) # Removed
            server_transcript = f"[Could not understand audio ({language_code})]"
        except sr.RequestError as e:
            # Could not request results from Google service (network issue, API key issue, etc.)
            # print(f"Could not request results from Google Speech Recognition service ({language_code}); {e}", flush=True) # Removed
            server_transcript = f"[Speech Recognition request failed ({language_code}): {e}]"
        except ValueError as ve:
             # Potentially catches issues if the language code format is wrong,
             # though recognize_google might raise RequestError or UnknownValueError instead.
             # print(f"Potential error with language code '{language_code}': {ve}", flush=True) # Removed
             server_transcript = f"[Error during transcription, possibly invalid language code: {language_code}]"
             language_used = "Error" # Indicate there was an issue with the language code used
        except Exception as sr_err:
             # Catch any other unexpected errors during recognition
             # print(f"An unexpected error occurred during speech recognition: {sr_err}", flush=True) # Removed
             # print(traceback.format_exc(), flush=True) # Uncomment for detailed traceback
             server_transcript = f"[Unexpected error during transcription ({language_code})]"


        # *** THIS IS THE KEY PRINT STATEMENT for the console ***
        # Print the final result (successful transcript or error message) to the console.
        print(f"--> TRANSCRIPT ({language_used}): {server_transcript}", flush=True)
        result = translator.detect(server_transcript)
        print(f"Detected language: {result.lang}, Confidence: {result.confidence}")
        if language_used==result:
            print('src language verifid and matched')
        result = translator.translate(server_transcript, src=result.lang, dest='en')
        print('****************')
        print(result.src)
        print(result.dest)
        print(result.text)
        print('****************')

        res="this will be the response"
        result = translator.translate(res, src='en', dest=result.src)
        print(result.text)




        # --- 6. Save Transcript Details to a Text File ---
        # This saves metadata along with both transcripts for record-keeping.
        # print(f"Saving transcript details to: {transcript_path}", flush=True) # Removed
        try:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Requested Language: {language_code}\n") # Log requested language
                f.write(f"Original File: {os.path.basename(original_audio_path)}\n")
                # Use wav_path which points to the correct WAV file (original or converted)
                f.write(f"Processed WAV File: {os.path.basename(wav_path)}\n")
                f.write(f"User transcript (from frontend): {user_transcript}\n")
                # Log the final transcript or status message along with the language used
                f.write(f"Server transcript ({language_used}): {server_transcript}\n")
            # print("Transcript details saved successfully.", flush=True) # Removed
        except Exception as write_err:
            # Optional: Log error if saving the transcript file fails
            print(f"Error saving transcript file '{transcript_path}': {write_err}", flush=True)


        # --- 7. Return Success JSON Response to Frontend ---
        # print("Processing complete. Returning success response.", flush=True) # Removed
        return jsonify({
            "message": "Audio received, processed, and transcription attempted.",
            "user_transcript": user_transcript,
            "server_transcript": server_transcript, # Send the result back to the client
            "language_used": language_used, # Send back language actually used
            "original_filename": original_filename,
            # Return paths for potential reference, though client might not need them
            "saved_original_path": original_audio_path,
            "saved_wav_path": wav_path,
            "saved_transcript_path": transcript_path
        }), 200

    except Exception as e:
        # --- Global Error Handling for the entire route ---
        # This catches errors not caught by more specific blocks above
        # (e.g., issues reading request data, unexpected OS errors)
        print(f"--> UNEXPECTED ERROR in /upload: {e}", flush=True)
        # print(traceback.format_exc(), flush=True) # Uncomment for detailed traceback in console
        return jsonify({
            "message": "An internal server error occurred during processing.",
            "error": str(e),
            "user_transcript": user_transcript, # Return whatever transcript info we had
            "server_transcript": server_transcript, # Return the last known status
            "language_used": language_used
        }), 500 # Indicate Internal Server Error

# -----------------------------------------------------------------------------
# Main Execution Block
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # This print confirms the server is starting, useful for console feedback.
    print(f"--- Flask server starting ---", flush=True)
    print(f"--- Uploads will be saved to: {os.path.abspath(UPLOAD_FOLDER)} ---", flush=True)
    print(f"--- Access the application at http://127.0.0.1:5000/ ---", flush=True)
    # Run the Flask development server
    # debug=True enables auto-reloading on code changes and provides debugger
    # host='0.0.0.0' would make it accessible on your network, not just localhost
    # port=5000 is the default Flask port
    app.run(debug=True, port=5000)