document.addEventListener('DOMContentLoaded', function() {
    // Initialize Dropzone
    Dropzone.autoDiscover = false;
    
    const myDropzone = new Dropzone("#documentDropzone", {
        url: "/upload",
        maxFilesize: 16, // MB
        maxFiles: 10,
        acceptedFiles: ".pdf,.doc,.docx,.txt",
        autoProcessQueue: false,
        addRemoveLinks: true,
        dictDefaultMessage: "Drop files here to upload",
        dictFileTooBig: "File is too big ({{filesize}}MB). Max filesize: {{maxFilesize}}MB.",
        dictInvalidFileType: "Invalid file type. Only PDF, DOC, DOCX, and TXT files are allowed.",
        dictResponseError: "Server error: {{statusCode}}",
        dictMaxFilesExceeded: "Maximum number of files exceeded.",
        dictRemoveFile: "Remove",
        
        // Display file preview for text files
        thumbnailWidth: 80,
        thumbnailHeight: 80,
        previewTemplate: `
            <div class="dz-preview dz-file-preview">
                <div class="dz-image">
                    <img data-dz-thumbnail />
                </div>
                <div class="dz-details">
                    <div class="dz-size"><span data-dz-size></span></div>
                    <div class="dz-filename"><span data-dz-name></span></div>
                </div>
                <div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>
                <div class="dz-error-message"><span data-dz-errormessage></span></div>
                <div class="dz-success-mark">
                    <svg width="54" height="54" viewBox="0 0 54 54" fill="white" xmlns="http://www.w3.org/2000/svg">
                        <path d="M10.8,28.5L20.7,38.7L43.2,16.2"/>
                    </svg>
                </div>
                <div class="dz-error-mark">
                    <svg width="54" height="54" viewBox="0 0 54 54" fill="white" xmlns="http://www.w3.org/2000/svg">
                        <path d="M14.1,14.1L39.9,39.9 M39.9,14.1L14.1,39.9"/>
                    </svg>
                </div>
                <div class="dz-remove" data-dz-remove>
                    <i class="fas fa-times"></i>
                </div>
            </div>
        `,
        
        init: function() {
            // Set up event handlers
            this.on("addedfile", function(file) {
                // Customize file preview based on file type
                if (file.type === "application/pdf") {
                    // PDF icon
                    file.previewElement.querySelector("img[data-dz-thumbnail]").src = "https://cdn-icons-png.flaticon.com/512/337/337946.png";
                } else if (file.type === "application/msword" || file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
                    // Word icon
                    file.previewElement.querySelector("img[data-dz-thumbnail]").src = "https://cdn-icons-png.flaticon.com/512/337/337932.png";
                } else {
                    // Text icon
                    file.previewElement.querySelector("img[data-dz-thumbnail]").src = "https://cdn-icons-png.flaticon.com/512/337/337956.png";
                }
            });
            
            this.on("success", function(file, response) {
                // Add success message
                const successElement = document.createElement("div");
                successElement.className = "alert alert-success mt-2";
                successElement.textContent = "File uploaded successfully!";
                document.querySelector(".card-body").appendChild(successElement);
                
                // Remove success message after 3 seconds
                setTimeout(function() {
                    successElement.remove();
                }, 3000);
                
                // Clear file list after 1 second
                setTimeout(() => {
                    myDropzone.removeFile(file);
                }, 1000);
            });
            
            this.on("error", function(file, errorMessage) {
                console.error("Upload error:", errorMessage);
            });
            
            this.on("complete", function() {
                // Check if all files have been processed
                if (myDropzone.getQueuedFiles().length === 0 && myDropzone.getUploadingFiles().length === 0) {
                    // All files have been processed
                    document.getElementById("uploadBtn").disabled = false;
                    document.getElementById("uploadBtn").innerHTML = '<i class="fas fa-upload me-1"></i> Upload All Files';
                    
                    // Refresh the page after a delay
                    setTimeout(function() {
                        window.location.reload();
                    }, 2000);
                }
            });
        }
    });
    
    // Handle upload button click
    document.getElementById("uploadBtn").addEventListener("click", function() {
        if (myDropzone.getQueuedFiles().length === 0) {
            alert("Please add files to upload.");
            return;
        }
        
        // Disable button during upload
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Uploading...';
        
        // Process all queued files
        myDropzone.processQueue();
    });
});
