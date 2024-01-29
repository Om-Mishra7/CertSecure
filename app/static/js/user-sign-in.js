let signinForm = document.getElementById('signin-form');

signinForm.addEventListener('submit', function (event) {
    event.preventDefault();
    let signinBtn = document.getElementById('signin-btn');
    signinBtn.disabled = true;
    signinBtn.innerText = 'Signing up...';

    let email = document.getElementById('email').value;
    let password = document.getElementById('password').value;

    if (email && password) {

        if (!String(email)
            .toLowerCase()
            .match(
                /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|.(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
            )) {
            signinBtn.disabled = false;
            signinBtn.innerHTML = 'Sign up';
            createAlert('Please enter a valid email address', 'danger');
            return;
        }

        if (String(password).length < 8) {
            signinBtn.disabled = false;
            signinBtn.innerHTML = 'Sign up';
            createAlert('Password must be at least 8 characters', 'danger');
            return;
        }

        if (String(password).length > 128) {
            signinBtn.disabled = false;
            signinBtn.innerHTML = 'Sign up';
            createAlert('Password must be less than 128 characters', 'danger');
            return;
        }
    }
    generateReCaptchaToken('user_signin').then(function (token) {

        fetch('/api/v1/sign-in', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                'email': email,
                'password': password,
                'token': token
            })
        }).then(function (response) {
            if (response.status !== 500) {
                return response.json();
            }
            else {
                createAlert('Our internal services are facing some issues, please try again later', 'danger');
                return;
            }
        }
        ).then(function (jsonResponse) {
            if (jsonResponse['status'] === 'success') {
                createAlert(jsonResponse["message"], 'success');
                setTimeout(function () {
                    window.location.href = '/sign-in';
                }, 5000);
            } else {
                createAlert(jsonResponse["message"], 'danger');
                return;
            }
        }).catch(function (error) {
            createAlert('Our internal services are facing some issues, please try again later', 'danger');
            return;
        }
        );
    }).catch(function (error) {
        createAlert('Unable to generate reCAPTCHA token, please try again later', 'danger');
        return;
    }
    ).finally(function () {
        signinBtn.disabled = false;
        signinBtn.innerHTML = 'Sign in';
    }
    );
}

);
