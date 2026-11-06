/**
 * Society Maintenance Management System - Client Side Interactive Scripts
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Toggle for Mobile / Tablet
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (event) {
            if (window.innerWidth < 992 &&
                sidebar.classList.contains('show') &&
                !sidebar.contains(event.target) &&
                !sidebarToggle.contains(event.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // 2. Generic Table Search & Filter Helper
    const tableSearchInput = document.getElementById('tableSearchInput');
    if (tableSearchInput) {
        tableSearchInput.addEventListener('keyup', function () {
            const filter = this.value.toLowerCase();
            const table = document.querySelector('.table-custom tbody');
            if (!table) return;
            const rows = table.getElementsByTagName('tr');

            for (let i = 0; i < rows.length; i++) {
                const text = rows[i].textContent || rows[i].innerText;
                if (text.toLowerCase().indexOf(filter) > -1) {
                    rows[i].style.display = '';
                } else {
                    rows[i].style.display = 'none';
                }
            }
        });
    }

    // 3. Demo Credentials Quick Filler
    const fillAdminBtn = document.getElementById('fillAdminDemo');
    const fillResidentBtn = document.getElementById('fillResidentDemo');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    if (fillAdminBtn && usernameInput && passwordInput) {
        fillAdminBtn.addEventListener('click', function () {
            usernameInput.value = 'admin';
            passwordInput.value = 'admin123';
        });
    }

    if (fillResidentBtn && usernameInput && passwordInput) {
        fillResidentBtn.addEventListener('click', function () {
            usernameInput.value = 'resident1';
            passwordInput.value = 'resident123';
        });
    }

    // 4. Delete Confirmation Interceptor
    const deleteForms = document.querySelectorAll('.confirm-delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            const itemName = this.getAttribute('data-item-name') || 'this record';
            const confirmed = confirm(`Are you sure you want to permanently delete ${itemName}? This action cannot be undone.`);
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // 5. Simulated Payment Gateway Form Behavior
    const paymentForm = document.getElementById('simulatedPaymentForm');
    const paymentSubmitBtn = document.getElementById('paymentSubmitBtn');
    const paymentProcessingSpinner = document.getElementById('paymentProcessingSpinner');

    if (paymentForm && paymentSubmitBtn) {
        paymentForm.addEventListener('submit', function (e) {
            e.preventDefault();
            // Show processing spinner
            paymentSubmitBtn.disabled = true;
            if (paymentProcessingSpinner) {
                paymentProcessingSpinner.classList.remove('d-none');
            }
            paymentSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing Payment Securely...';

            // Simulate gateway latency of 1.2 seconds then submit form
            setTimeout(() => {
                paymentForm.submit();
            }, 1200);
        });
    }
});

// Helper for print
function printReceipt() {
    window.print();
}
