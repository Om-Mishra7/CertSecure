let signupForm = document.getElementById('signup-form');

let organizationDomainAddress = document.getElementById('organization-domain-address');

document.getElementById('organization-domain-address').addEventListener('keyup', function (event) {
    let organizationDomainAddress = this.value;

    // Remove protocols (http:// or https://)
    if (organizationDomainAddress.match(/^(http:\/\/|https:\/\/)/)) {
        createAlert('Organization domain must not contain protocols', 'danger');
        organizationDomainAddress = organizationDomainAddress.replace(/^(http:\/\/|https:\/\/)/, '');
    }

    // Remove special characters except hyphens and . (dot)
    if (organizationDomainAddress.match(/[^a-zA-Z0-9-.]/g)) {
        createAlert('Organization domain must not contain special characters', 'danger');
        organizationDomainAddress = organizationDomainAddress.replace(/[^a-zA-Z0-9-.]/g, '');
    }

    // Remove trailing slashes
    if (organizationDomainAddress.match(/\/$/)) {
        createAlert('Organization domain must not contain trailing slashes', 'danger');
        organizationDomainAddress = organizationDomainAddress.replace(/\/$/, '');
    }

    // Update the value in the input field
    this.value = organizationDomainAddress;
});

document.getElementById('organization-email').addEventListener('keyup', function (event) {
    let organizationEmail = this.value;

    // Remove trailing spaces
    if (organizationEmail.match(/\s$/)) {
        createAlert('Organization email must not contain trailing spaces', 'danger');
        organizationEmail = organizationEmail.replace(/\s$/, '');
    }

    // Update the value in the input field
    this.value = organizationEmail;
}

);

document.getElementById('organization-confirm-password').addEventListener('keyup', function (event) {

    setTimeout(function () {
        let organizationPassword = document.getElementById('organization-password').value;
        let organizationConfirmPassword = document.getElementById('organization-confirm-password').value;
        if (organizationPassword != organizationConfirmPassword) {
            createAlert('The passwords do not match, please try again', 'danger');
        }
    }
        , 2000);

}


);

signupForm.addEventListener('submit', function (event) {
    event.preventDefault();
    let signupBtn = document.getElementById('signup-btn');
    signupBtn.disabled = true;
    signupBtn.innerText = 'Signing up...';
    let organizationName = document.getElementById('organization-name').value;
    let organizationDomainAddress = document.getElementById('organization-domain-address').value;
    let organizationEmail = document.getElementById('organization-email').value;
    let organizationPhone = document.getElementById('organization-phone').value;
    let organizationPassword = document.getElementById('organization-password').value;
    let organizationConfirmPassword = document.getElementById('organization-confirm-password').value;
    let organizationIndustry = document.getElementById('organization-industry').value;
    let organizationSize = document.getElementById('organization-size').value;
    let organizationCountry = document.getElementById('organization-country').value;

    if (organizationName && organizationDomainAddress && organizationEmail && organizationPhone && organizationPassword && organizationConfirmPassword && organizationIndustry && organizationSize && organizationCountry) {

        if (!String(organizationEmail)
            .toLowerCase()
            .match(
                /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|.(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
            )) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Please enter a valid email address', 'danger');
            return;
        }

        if (String(organizationName).length < 3) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Organization name must be at least 3 characters', 'danger');
            return;
        }

        if (String(organizationName).length > 128) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Organization name must be less than 128 characters', 'danger');
            return;
        }

        if (String(organizationDomainAddress).length < 3) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Organization domain address must be at least 3 characters', 'danger');
            return;
        }

        if (String(organizationDomainAddress).length > 128) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Organization domain address must be less than 128 characters', 'danger');
            return;
        }

        if (String(organizationPassword).length < 8) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Password must be at least 8 characters', 'danger');
            return;
        }

        if (String(organizationPassword).length > 128) {
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            createAlert('Password must be less than 128 characters', 'danger');
            return;
        }

        if (String(organizationPassword) !== String(organizationConfirmPassword)) {
            createAlert('The passwords do not match, please try again', 'danger');
            signupBtn.disabled = false;
            signupBtn.innerHTML = 'Sign up';
            return;
        }
    }

    generateReCaptchaToken('organization_signup').then(function (token) {

        fetch('/api/v1/organization/sign-up', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                organization_name: organizationName,
                organization_domain_address: organizationDomainAddress,
                organization_email: organizationEmail,
                organization_phone: organizationPhone,
                organization_password: organizationPassword,
                organization_confirm_password: organizationConfirmPassword,
                organization_industry: organizationIndustry,
                organization_size: organizationSize,
                organization_country: organizationCountry,
                recaptcha_token: token
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
                    window.location.href = '/organization/domain-verification';
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
        signupBtn.disabled = false;
        signupBtn.innerHTML = 'Sign up';
    }
    );
}

);
