// PDF generation utility functions
function generatePDF(elementId, filename) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.error('Element not found:', elementId);
        return;
    }

    // Add print styles
    const style = document.createElement('style');
    style.textContent = `
        /* Hide interactive elements */
        .btn,
        .card-footer form,
        .card-header form,
        .card-footer .btn-info,
        .dropdown,
        .d-flex .btn-primary,
        .action-buttons,
        form,
        .border-top,
        #saveNutritionBtn,
        #analyzeBtn,
        .card-header .action-buttons,
        .modal { 
            display: none !important;
        }
        /* General print styles for better alignment and readability */
        body {
            font-family: sans-serif;
            color: #333;
            -webkit-print-color-adjust: exact; /* For background colors */
        }
        .container {
            max-width: 100% !important;
            padding: 20px !important;
            margin: 0 auto !important;
        }
        h1, h4, h5 {
            page-break-after: avoid;
        }
        table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin-bottom: 1rem !important;
        }
        th, td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
            text-align: left !important;
        }
        .card {
            border: 1px solid #dee2e6 !important;
            border-radius: 0.375rem !important;
            box-shadow: none !important;
            margin: 0 auto !important;
            max-width: 800px !important;
        }
        .card-header {
            background: #f8f9fa !important;
            color: #000 !important;
            border-bottom: 1px solid #dee2e6 !important;
            padding: 1rem 1.5rem !important;
            border-radius: 0.375rem 0.375rem 0 0 !important;
        }
        .card-body {
            padding: 1.5rem !important;
        }
        .row {
            margin: 0 !important;
        }
        .col-md-12, .col-md-5, .col-md-7 {
            padding: 0 15px !important;
        }
        .text-center {
            text-align: center !important;
        }
        .text-muted {
            color: #6c757d !important;
        }
        .list-group-item {
            border: 1px solid #dee2e6 !important;
            padding: 0.75rem 1.25rem !important;
        }
        .bg-light {
            background-color: #f8f9fa !important;
        }
        .rounded {
            border-radius: 0.375rem !important;
        }
        .mb-4 {
            margin-bottom: 1.5rem !important;
        }
        .mb-4:last-child {
            margin-bottom: 0 !important;
        }
        .mt-4 {
            margin-top: 1.5rem !important;
        }
        .p-2 {
            padding: 0.5rem !important;
        }
        .m-1 {
            margin: 0.25rem !important;
        }
        h5 {
            font-size: 1.25rem !important;
            font-weight: 500 !important;
            margin-bottom: 1rem !important;
        }
        .fas {
            font-family: "Font Awesome 5 Free" !important;
        }
    `;
    document.head.appendChild(style);

    // PDF options
    const opt = {
        margin: 10,
        filename: filename,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
            scale: 2,
            useCORS: true,
            letterRendering: true,
            scrollY: 0
        },
        jsPDF: {
            unit: 'mm',
            format: 'a4',
            orientation: 'portrait'
        }
    };

    // Generate PDF
    html2pdf().set(opt).from(element).save().then(() => {
        style.remove();
    }).catch(err => {
        console.error('PDF generation failed:', err);
        style.remove();
    });
}
