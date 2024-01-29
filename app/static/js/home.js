//Logic for the appearing of the glowbars
let productivitySectionSVGContainer = document.getElementById("productivity-section-glowbar-line-svg-container");
let productivitySectionGlowbarLine = document.getElementById("productivity-section-glowbar-line");

let decentralizationSectionSVGContainer = document.getElementById("decentralization-section-glowbar-line-svg-container");
let decentralizationSectionGlowbarLine = document.getElementById("decentralization-section-glowbar-line");

window.addEventListener("scroll", function () {
    let oneThirdPosition = productivitySectionSVGContainer.getBoundingClientRect().top + productivitySectionSVGContainer.offsetHeight * (2 / 3);


    if (oneThirdPosition < window.innerHeight) {
        if (productivitySectionGlowbarLine.classList.contains("animate-glowbar")) {
            productivitySectionGlowbarLine.classList.remove("animate-glowbar");
        }
        productivitySectionGlowbarLine.classList.add("animate-glowbar");
    }
    else {
        if (productivitySectionGlowbarLine.classList.contains("animate-glowbar")) {
            productivitySectionGlowbarLine.classList.remove("animate-glowbar");
        }
    }

    let twoThirdPosition = decentralizationSectionSVGContainer.getBoundingClientRect().top + decentralizationSectionSVGContainer.offsetHeight * (1 / 3);

    if (twoThirdPosition < window.innerHeight) {
        if (decentralizationSectionGlowbarLine.classList.contains("animate-glowbar")) {
            decentralizationSectionGlowbarLine.classList.remove("animate-glowbar");
        }
        decentralizationSectionGlowbarLine.classList.add("animate-glowbar");
    }

    else {
        if (decentralizationSectionGlowbarLine.classList.contains("animate-glowbar")) {
            decentralizationSectionGlowbarLine.classList.remove("animate-glowbar");
        }
    }

});


// Div tilt effect on hover

let hoverableDivs = document.getElementsByClassName("hoverable-div");

for (let i = 0; i < hoverableDivs.length; i++) {
    hoverableDivs[i].addEventListener("mouseenter", function (event) {
        animateTilt(event.target, event.clientX, event.clientY);
    });

    hoverableDivs[i].addEventListener("mouseleave", function (event) {
        resetTilt(event.target);
    });
}

function animateTilt(div, mouseX, mouseY) {
    
    let rect = div.getBoundingClientRect();
    let divCenterX = rect.left + rect.width / 2;
    let divCenterY = rect.top + rect.height / 2;

    let rotateX = (mouseY - divCenterY) / 50;
    let rotateY = (mouseX - divCenterX) / 50;

    div.style.transform = "rotateX(" + rotateX + "deg) rotateY(" + rotateY + "deg)";

}

function resetTilt(div) {
    div.style.transform = "rotateX(0deg) rotateY(0deg)";
}

