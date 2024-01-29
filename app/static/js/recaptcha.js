function generateReCaptchaToken(action) {
    return new Promise(function (resolve, reject) {
        grecaptcha.ready(function () {
            grecaptcha.execute('6LdINlonAAAAAK5yArQKUqdHU7sIM8lWD_t_ttOU', { action: action }).then(function (token) {
                resolve(token);
            }).catch(function (error) {
                reject(error);
            }
            );
        }
        );
    }
    );
}