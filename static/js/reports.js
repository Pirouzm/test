document.addEventListener('DOMContentLoaded', function() {
    // Add click event to report cards if not in view mode
    const reportCards = document.querySelectorAll('.report-card');
    
    reportCards.forEach(card => {
        card.addEventListener('click', function() {
            const reportId = this.getAttribute('data-report-id');
            window.location.href = `/reports/${reportId}`;
        });
    });
    
    // Print functionality
    const printBtn = document.getElementById('printReportBtn');
    if (printBtn) {
        printBtn.addEventListener('click', function() {
            window.print();
        });
    }
    
    // Format report content for better readability
    const reportContent = document.querySelector('.report-content');
    if (reportContent) {
        // Add some basic formatting
        const formattedContent = reportContent.innerHTML
            // Add heading styles
            .replace(/^(.*EMOTIONAL SUPPORT ANIMAL.*REPORT.*)$/gm, '<h2 class="text-center mb-4">$1</h2>')
            // Format section headers
            .replace(/^([0-9]+\.\s.+:)$/gm, '<h4 class="mt-4 mb-3">$1</h4>')
            // Format dates
            .replace(/(Date:\s)(.+)/g, '$1<strong>$2</strong>')
            // Format disclaimers
            .replace(/(DISCLAIMER:.+)/g, '<div class="alert alert-warning mt-3">$1</div>')
            .replace(/(IMPORTANT NOTICE:.+(?:\n.+)*)/g, '<div class="alert alert-info mt-3">$1</div>');
            
        reportContent.innerHTML = formattedContent;
    }
});
