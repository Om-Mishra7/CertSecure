let domainVerificationForm = document.getElementById('domain-verification-form');

if (domainVerificationForm) {
    domainVerificationForm.addEventListener('submit', (event) => {
        event.preventDefault();
        let domainVerificationButton = document.getElementById('domain-verification-submit-btn');
        let domainVerificationStatus = document.getElementById('domain-verification-status');
        domainVerificationButton.disabled = true;
        domainVerificationStatus.innerText = 'Verifying...';
        generateReCaptchaToken('organization_signup').then(function (token) {

            fetch('/api/v1/organization/domain-verification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    token: token
                })
            }).then(function (response) {
                if (response.status !== 500) {
                    return response.json();
                }
                else {
                    createAlert('Our internal services are facing some issues, please try again later', 'danger');
                    return;
                }
            }).then(function (jsonResponse) {
                if (jsonResponse.status === 'success') {
                    domainVerificationButton.disabled = false;
                    domainVerificationStatus.innerText = 'Verified';
                    createAlert(jsonResponse.message, 'success');
                    setTimeout(function () {
                        window.location.href = '/sign-in';
                    }
                        , 5000);
                    return;

                } else {
                    domainVerificationButton.disabled = false;
                    domainVerificationStatus.innerText = 'Not verified';
                    createAlert(jsonResponse.message, 'danger');
                    return;
                }
            }).catch(function (error) {
                domainVerificationButton.disabled = false;
                domainVerificationStatus.innerText = 'Not verified';
                createAlert('Our internal services are facing some issues, please try again later', 'danger');
                return;
            });
        }
        ).catch(function (error) {
            domainVerificationButton.disabled = false;
            domainVerificationButton.innerText = 'Verify';
            domainVerificationStatus.innerText = 'Not verified';
            createAlert('Unable to generate reCAPTCHA token, please try again later', 'danger');
            return;
        }
        )
            .finally(function () {
                domainVerificationButton.disabled = false;
                domainVerificationButton.innerText = 'Verify';
            });
    }
    );
}
