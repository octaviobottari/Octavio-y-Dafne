document.addEventListener("DOMContentLoaded", () => {
    const items = document.querySelectorAll(".item");

    items.forEach((item, index) => {
        const reserveButton = item.querySelector(".reserve-button");
        const reserveForm = item.querySelector(".reserve-form");
        const reservedBy = item.querySelector(".reserved-by");

        if (reserveButton) {
            reserveButton.addEventListener("click", () => {
                reserveForm.style.display = "block";
                reserveButton.style.display = "none";
            });

            reserveForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const nameInput = reserveForm.querySelector("#name");
                const name = nameInput.value.trim();

                if (name) {
                   
                    fetch("/api/reservations", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            item_id: index, 
                            name: name,
                        }),
                    })
                    .then((response) => {
                        if (!response.ok) {
                            return response.json().then((data) => {
                                throw new Error(data.error || "Error al reservar");
                            });
                        }
                        return response.json();
                    })
                    .then((data) => {
                        reservedBy.textContent = `Reservado por: ${name}`;
                        reservedBy.style.display = "block";
                        reserveForm.style.display = "none";
                        reserveButton.disabled = true;
                        reserveButton.textContent = "Reservado";
                    })
                    .catch((error) => {
                        alert(error.message);
                        reserveForm.style.display = "none";
                        reserveButton.style.display = "block";
                    });
                } else {
                    alert("Por favor, ingresa tu nombre.");
                }
            });
        }
    });
});

