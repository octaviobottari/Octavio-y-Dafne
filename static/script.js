document.addEventListener("DOMContentLoaded", () => {
    const items = document.querySelectorAll(".item");

    items.forEach((item) => {
        const reserveButton = item.querySelector(".reserve-button");
        const reserveForm = item.querySelector(".reserve-form");
        const reservedBy = item.querySelector(".reserved-by");
        const itemId = reserveButton ? reserveButton.getAttribute("data-item-id") : null;

        if (reserveButton) {
            reserveButton.addEventListener("click", () => {
                reserveForm.style.display = "block";
                reserveButton.style.display = "none";
            });

            reserveForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const nameInput = reserveForm.querySelector(`#name-${itemId}`);
                const contactInput = reserveForm.querySelector(`#contact-${itemId}`);
                const name = nameInput.value.trim();
                const contact = contactInput.value.trim();

                if (name && contact) {
                    try {
                        const response = await fetch("/api/reservations", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                                item_id: itemId,
                                name: name,
                                contact: contact
                            }),
                        });

                        const data = await response.json();
                        if (!response.ok) {
                            throw new Error(data.error || "Error al reservar");
                        }

                        reservedBy.textContent = `Reservado por: ${name} (${contact}) - ${new Date().toLocaleString()}`;
                        reservedBy.style.display = "block";
                        reserveForm.style.display = "none";
                        reserveButton.style.display = "none";
                    } catch (error) {
                        alert(error.message);
                        reserveForm.style.display = "none";
                        reserveButton.style.display = "block";
                    }
                } else {
                    alert("Por favor, ingresa tu nombre y número de contacto.");
                }
            });
        }
    });
});