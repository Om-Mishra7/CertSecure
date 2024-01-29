function createAlert(message, type) {
    let alertDiv = document.getElementById('alert-div');
    alertDiv.classList.remove('alert-danger', 'alert-success', 'alert-warning', 'alert-info', 'fade-out');
    alertDiv.classList.add('alert-' + type, 'fade-in');

    let alertMessage = document.getElementById('alert-message');
    alertMessage.innerHTML = message;

    alertDiv.style.display = 'flex';
    alertDiv.style.opacity = '0';

    clearTimeout(alertDiv.fadeOutTimeout);

    alertDiv.fadeOutTimeout = setTimeout(function () {
        alertDiv.classList.remove('fade-in');
        alertDiv.classList.add('fade-out');
    }, 3000);
}


function closeAlert() {
    let alertDiv = document.getElementById('alert-div');
    alertDiv.classList.remove('fade-in');
    alertDiv.classList.add('fade-out');
}

function displayNotProductionWarning() {
    const metas = document.getElementsByTagName('meta');
    let appMode = null;

    for (let i = 0; i < metas.length; i++) {
        if (metas[i].getAttribute('name') === "app-mode") {
            appMode = metas[i].getAttribute('content');
        }
    }

    if (appMode != null) {

        if (appMode == 'testing') {
            createAlert('This is a test build of CertSecure, and may contain bugs. Please report any bugs to the developer.', 'warning');
            return;
        }

        if (appMode == 'development') {
            createAlert('This is a development build of CertSecure, and may contain bugs. Please report any bugs to the developer.', 'warning');
            return;
        }
    }

    return;
}

function linkTracking() {
    links = document.querySelectorAll('a');

    for (let i = 0; i < links.length; i++) {
        if (links[i].getAttribute('href').includes('http')) {
            links[i].setAttribute('rel', 'noreferrer');

            if (!links[i].getAttribute('href').includes(window.location.hostname)) {
                links[i].addEventListener('click', function (event) {
                    event.preventDefault();
                    createAlert('You are about to leave CertSecure. Please ensure you trust the site you are about to visit.', 'info');
                    setTimeout(function () {
                        window.open(links[i].getAttribute('href'), '_blank');
                    }, 5000);
                });
            }

        }
    }
}


document.onreadystatechange = function () {
    if (document.readyState === 'complete') {
        if (document.querySelector("#loader") !== null) {
            document.querySelector("#loader").style.visibility = "hidden";

        };

        displayNotProductionWarning();
        linkTracking();

        // Add a class .top-navbar-scrolled to the top-navbar when the page is scrolled
        if (document.getElementById("top-navbar") !== null) {
            document.addEventListener('scroll', scrollFunction);
        }

        if (document.getElementById("downward-container") !== null) {
            document.addEventListener('scroll', scrollFunctionDownwardContainer);
        }

        // Check if URL has a argument called message, and if so, display it as an alert
        const queryString = window.location.search;
        const urlParams = new URLSearchParams(queryString);
        const message = urlParams.get('message');

        if (message != null) {
            createAlert(message, 'info');
        }


    }
};

function scrollFunction() {
    if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
        document.getElementById("top-navbar").classList.add('top-navbar-scrolled');
    } else {
        document.getElementById("top-navbar").classList.remove('top-navbar-scrolled');
    }
}

function scrollFunctionDownwardContainer() {
    console.log('test');
    console.log(document.body.scrollTop);
    if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
        document.getElementById("downward-container").setAttribute('style', 'display: none;');
    } else {
        document.getElementById("downward-container").setAttribute('style', 'display: flex;');
    }
}


function toggleNav() {


    let nav = document.getElementById('nav');

    if (nav.classList.contains('nav-open')) {
        let navToggle = document.getElementById('nav-toggle');
        navToggle.animate([
            { transform: 'rotate(180deg)' },
            { transform: 'rotate(0deg)' }
        ], {
            duration: 500,
            easing: 'ease-in-out',
            fill: 'forwards'
        });
        nav.classList.remove('nav-open');
        nav.classList.add('nav-closed');

    }
    else {

        if (window.innerWidth <= 768) {
            return;
        }
        nav.classList.remove('nav-closed');
        let navToggle = document.getElementById('nav-toggle');
        navToggle.animate([
            { transform: 'rotate(0deg)' },
            { transform: 'rotate(180deg)' }
        ], {
            duration: 500,
            easing: 'ease-in-out',
            fill: 'forwards'
        });
        nav.classList.add('nav-open');
        nav.addEventListener('click', function (event) {
            if (event.target.id == 'nav') {
                toggleNav();
            }

        }
        );
    }
}

function toggleHamburger() {
    hamburgerMenu = document.getElementById('hamburger-menu');
    hamburgerMenuIcon = document.getElementById('hamburger-icon');


    if (hamburgerMenu.classList.contains('closed')) {
        hamburgerMenu.classList.remove('closed');
        hamburgerMenuIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 -960 960 960" width="24"><path d="M256-213.847 213.847-256l224-224-224-224L256-746.153l224 224 224-224L746.153-704l-224 224 224 224L704-213.847l-224-224-224 224Z"/></svg>';
    }
    else {
        hamburgerMenu.classList.add('closed');
        hamburgerMenuIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 -960 960 960" width="24"><path d="M140.001-254.616v-59.999h679.998v59.999H140.001Zm0-195.385v-59.998h679.998v59.998H140.001Zm0-195.384v-59.999h679.998v59.999H140.001Z"/></svg>';
    }


}


function resendVerificationEmail() {
    fetch('/api/v1/resend-verification-email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 'email': document.getElementById('email').value })
    })
        .then(response => response.json())
        .then(data => {
            if (data['status'] == 'success') {
                createAlert(data['message'], 'success');
            }
            else {
                createAlert('We were unable to send you a verification email. Please try again later.', 'danger');
            }
        });

}

function toggleProfileDropdown(event) {
    let profileDropdown = document.getElementById('profile-dropdown');

    if (profileDropdown.classList.contains('profile-closed')) {
        profileDropdown.classList.remove('profile-closed');
    }
    else {
        profileDropdown.classList.add('profile-closed');
    }

    event.stopPropagation();

    document.addEventListener('click', function (event) {
        if (event.target.id != 'profile-dropdown' && event.target.id != 'profile-dropdown-button') {
            if (!profileDropdown.classList.contains('profile-closed')) {
                profileDropdown.classList.add('profile-closed');
            }
        }
    });
}