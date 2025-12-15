// --- Dummy Detection Info (demo only) ---
const details = document.getElementById('details');
setInterval(() => {
  const confidence = (85 + Math.random() * 15).toFixed(1);
  const distance = (2 + Math.random() * 3).toFixed(1);
  const time = new Date().toLocaleTimeString();
  details.innerHTML = `
    <p><strong>Person:</strong> Detected</p>
    <p><strong>Confidence:</strong> ${confidence}%</p>
    <p><strong>Distance:</strong> ${distance} m</p>
    <p><strong>Time:</strong> ${time}</p>
  `;
}, 4000);

// --- Rover Control Logic (Based on previous request) ---

// Function to send control data to the FastAPI server
function sendControlToRover(x, y) {
    // You may need to change 'localhost:8000' to your Raspberry Pi's IP address and port
    const serverURL = "http://100.119.95.125:8000"; 
    
    const url = `${serverURL}/move?x=${x.toFixed(2)}&y=${y.toFixed(2)}`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                console.error("Failed to send control command:", response.statusText);
            }
        })
        .catch(error => console.error("Error sending control command:", error));
}


// --- Joystick System ---
const base = document.getElementById("joystick-base");
const knob = document.getElementById("joystick-knob");
const output = document.getElementById("joystick-output");

// Wait for the DOM to load before getting dimensions
window.onload = () => {
    // Recalculate dimensions on load to ensure accuracy
    const baseRect = base.getBoundingClientRect();
    const baseCenter = { x: baseRect.width / 2, y: baseRect.height / 2 };
    const maxDistance = baseRect.width / 2 - knob.offsetWidth / 2;
    
    let active = false;

    function updateJoystick(clientX, clientY) {
        const rect = base.getBoundingClientRect();
        const x = clientX - rect.left;
        const y = clientY - rect.top;

        const dx = x - baseCenter.x;
        const dy = y - baseCenter.y;
        const distance = Math.min(Math.sqrt(dx * dx + dy * dy), maxDistance);
        const angle = Math.atan2(dy, dx);

        const knobX = baseCenter.x + distance * Math.cos(angle);
        const knobY = baseCenter.y + distance * Math.sin(angle);

        knob.style.transform = `translate(${knobX - baseCenter.x - knob.offsetWidth / 2}px, ${knobY - baseCenter.y - knob.offsetHeight / 2}px)`;

        const normalizedX = (distance / maxDistance) * Math.cos(angle);
        const normalizedY = (distance / maxDistance) * Math.sin(angle);

        // Invert Y to match traditional robot control (Positive Y = Forward/Up)
        const roverY = -normalizedY; 

        output.innerText = `x: ${normalizedX.toFixed(2)}, y: ${roverY.toFixed(2)}`;

        // Send control data
        sendControlToRover(normalizedX, roverY);
    }

    function resetJoystick() {
        knob.style.transform = "translate(-50%, -50%)";
        output.innerText = "x: 0, y: 0";
        // Send stop command
        sendControlToRover(0, 0); 
    }

    // Mouse / Touch Events
    base.addEventListener("mousedown", (e) => {
        e.preventDefault(); // Prevent text selection
        active = true;
        updateJoystick(e.clientX, e.clientY);
    });

    document.addEventListener("mousemove", (e) => {
        if (active) updateJoystick(e.clientX, e.clientY);
    });

    document.addEventListener("mouseup", () => {
        if (active) {
            active = false;
            resetJoystick();
        }
    });

    base.addEventListener("touchstart", (e) => {
        e.preventDefault();
        active = true;
        updateJoystick(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: false });

    document.addEventListener("touchmove", (e) => {
        if (active) updateJoystick(e.touches[0].clientX, e.touches[0].clientY);
    });

    document.addEventListener("touchend", () => {
        if (active) {
            active = false;
            resetJoystick();
        }
    });
};