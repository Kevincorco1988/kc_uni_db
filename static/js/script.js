document.addEventListener("DOMContentLoaded", function() {
    // Select all elements with the class "scroll-to-table"
    var scrollButtons = document.querySelectorAll('.scroll-to-table');

    // Add click event listeners to each button
    scrollButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            console.log('Button clicked');

            // Get the target ID from the button's data-target attribute
            var targetId = button.getAttribute('data-target');
            console.log('Target ID:', targetId);

            // Check if the target element exists
            var targetElement = document.getElementById(targetId);
            if (targetElement) {
                console.log('Target element found:', targetElement);
                
                // Scroll smoothly to the target element
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            } else {
                console.error('Target element not found!');
            }
        });
    });
});



