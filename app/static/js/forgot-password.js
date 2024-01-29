function forgotPassword(event) {
    event.preventDefault();
    let email = document.getElementById('email').value;

    if (email === '') {
        createAlert('Please enter a valid email address.', 'danger');
        return;
    }


    generateReCaptchaToken('forgot_password').then(function (token) {
        let data = {
            email: email,
            token: token
        };

        fetch('/api/v1/forgot-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data),
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
                    window.location.href = '/home';
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
    );
}

