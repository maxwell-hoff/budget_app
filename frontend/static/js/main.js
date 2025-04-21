document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('statement-file');
    const uploadForm = document.getElementById('upload-form');
    const balanceDisplay = document.getElementById('latest-balance');

    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        fetch('/api/parse-statement', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            // Display the latest balance
            balanceDisplay.textContent = `$${data.latest_balance.toFixed(2)}`;
            balanceDisplay.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while processing the file.');
        });
    });
}); 