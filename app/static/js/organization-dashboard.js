function checkCertificate(event) {
    event.preventDefault();

    let certificateID = document.getElementById("certificate-id").value;

    if (certificateID === "") {
        createAlert("Please enter a certificate ID.", "danger");
        return;
    }

    window.location.href = "/certificate/" + certificateID;
}