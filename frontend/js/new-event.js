document.addEventListener("DOMContentLoaded", () => {
    // Initialize form submission handler
    const form = document.getElementById("new-event-form")
    form.addEventListener("submit", handleFormSubmit)
  
    // Add a direct click handler to the save button as a backup
    const saveButton = document.getElementById("save-event")
    saveButton.addEventListener("click", (e) => {
      e.preventDefault() // Prevent any default button behavior
      handleFormSubmit(e)
    })
  
    // Initialize audio recording
    initAudioRecording()
  
    // Initialize image upload preview
    const imageUpload = document.getElementById("image-upload")
    imageUpload.addEventListener("change", handleImageUpload)
  
    // Initialize audio blobs array
    window.audioBlobs = []
  })
  
  // Declare CONFIG variable
  const CONFIG = {
    API_URL: `${API_URL}/events/new`, // Replace with your actual API URL
  }
  
  async function handleFormSubmit(event) {
    // Prevent the default form submission behavior which causes page refresh
    if (event) {
      event.preventDefault()
      event.stopPropagation() // Also stop event propagation
    }
  
    const saveButton = document.getElementById("save-event")
    const saveSpinner = document.getElementById("save-spinner")
    const saveText = saveButton.querySelector(".save-text")
  
    // Disable button and show spinner
    saveButton.disabled = true
    saveSpinner.classList.remove("d-none")
    saveText.textContent = "Processing..."
  
    // Get form data
    const notes = document.getElementById("notes").value
    const imageUpload = document.getElementById("image-upload")
  
    // Create FormData object
    const formData = new FormData()
    formData.append("notes", notes)
  
    // Attach all audio recordings
    if (window.audioBlobs && window.audioBlobs.length > 0) {
      window.audioBlobs.forEach((blob, index) => {
        formData.append("audio_files", blob, `recording_${index}.wav`)
      })
    }
  
    // Attach images
    if (imageUpload.files.length > 0) {
      for (let i = 0; i < imageUpload.files.length; i++) {
        formData.append("images", imageUpload.files[i])
      }
    }
  
    try {
      console.log("Sending request to server...")
      const response = await fetch(`${CONFIG.API_URL}/events/new`, {
        method: "POST",
        body: formData,
      })
  
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }
  
      const data = await response.json()
      console.log("Server response:", data)
  
      if (!data || !data.id) {
        throw new Error("Invalid response: missing event ID")
      }
  
      console.log("Event created successfully:", data)
      saveText.textContent = "Success!"
  
      // Wait for 1 second to show success message
      await new Promise((resolve) => setTimeout(resolve, 1000))
  
      // Redirect to index page after successful API response
      window.location.href = "index.html"
    } catch (error) {
      console.error("Error details:", error)
      saveText.textContent = "Save Event"
  
      if (!window.navigator.onLine) {
        showError("You are offline. Please check your internet connection.")
      } else if (error.message.includes("Failed to fetch")) {
        showError("Unable to connect to server. Please ensure the backend service is running.")
      } else {
        showError(`Error creating event: ${error.message}`)
      }
    } finally {
      saveButton.disabled = false
      saveSpinner.classList.add("d-none")
    }
  }
// Add this helper function for showing errors
function showError(message) {
    // Create error alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Add alert to the top of the form
    const form = document.getElementById('new-event-form');
    form.insertBefore(alertDiv, form.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}

function initAudioRecording() {
    const startButton = document.getElementById('start-recording');
    const stopButton = document.getElementById('stop-recording');
    const recordingStatus = document.getElementById('recording-status');
    const recordingsList = document.getElementById('recordings-list');

    let mediaRecorder;
    let audioChunks = [];

    startButton.addEventListener('click', async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });

            mediaRecorder.addEventListener('stop', async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                audioChunks = [];

                // Add to recordings array
                window.audioBlobs.push(audioBlob);

                // Create audio element for preview
                const recordingItem = document.createElement('div');
                recordingItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                recordingItem.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="fas fa-file-audio me-2"></i>
                        <span>Recording ${window.audioBlobs.length}</span>
                        <audio class="ms-3" controls>
                            <source src="${URL.createObjectURL(audioBlob)}" type="audio/wav">
                        </audio>
                    </div>
                    <button class="btn btn-danger btn-sm delete-recording" data-index="${window.audioBlobs.length - 1}">
                        <i class="fas fa-trash"></i>
                    </button>
                `;

                recordingsList.appendChild(recordingItem);

                // Add delete handler
                recordingItem.querySelector('.delete-recording').addEventListener('click', function () {
                    const index = parseInt(this.getAttribute('data-index'));
                    window.audioBlobs.splice(index, 1);
                    recordingItem.remove();
                    // Update indices for remaining recordings
                    updateRecordingIndices();
                });

                startButton.classList.remove('d-none');
                stopButton.classList.add('d-none');
                recordingStatus.textContent = 'Recording saved';
            });

            mediaRecorder.start();
            startButton.classList.add('d-none');
            stopButton.classList.remove('d-none');
            recordingStatus.textContent = 'Recording... (click Stop when finished)';
        } catch (error) {
            console.error('Error starting recording:', error);
            recordingStatus.textContent = 'Error accessing microphone.';
        }
    });

    stopButton.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    });
}

function updateRecordingIndices() {
    const recordings = document.querySelectorAll('#recordings-list .list-group-item');
    recordings.forEach((item, index) => {
        item.querySelector('span').textContent = `Recording ${index + 1}`;
        item.querySelector('.delete-recording').setAttribute('data-index', index);
    });
}

function handleImageUpload(event) {
    const previewContainer = document.getElementById('image-preview');
    previewContainer.innerHTML = '';

    const files = event.target.files;

    if (files.length > 0) {
        for (let i = 0; i < files.length; i++) {
            const file = files[i];

            if (!file.type.startsWith('image/')) {
                continue;
            }

            const reader = new FileReader();

            reader.onload = function (e) {
                const imgContainer = document.createElement('div');
                imgContainer.className = 'image-container';

                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Image preview';

                imgContainer.appendChild(img);
                previewContainer.appendChild(imgContainer);
            };

            reader.readAsDataURL(file);
        }
    }
}