function resetPassword(event) {
    event.preventDefault();

    let password = document.getElementById("password").value;

    if (password === '') {
        createAlert('Please enter a valid password', 'danger');
        return;
    }

    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    const reset_token = urlParams.get('token');

    if (reset_token === null) {
        createAlert('No valid token was found in the URL, please check your email again', 'danger');
        return;
    }


    generateReCaptchaToken('reset_password').then(function (token) {
        let data = {
            password: password,
            token: token,
            reset_token: reset_token
        };

        fetch('/api/v1/reset-password', {
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
    });
}

