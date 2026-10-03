/* =========================================================
   EventEase – Main JavaScript
   Each feature is a small function that only runs if the
   page contains the elements it needs.
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
    initNavbar();
    initToasts();
    initScrollReveal();
    initCounters();
    initPasswordToggle();
    initPasswordStrength();
    initFormValidation();
    initConfirmForms();
    initPrintButtons();
    initCopyButtons();
    initAutoSubmit();
    initCountdown();
    initTabs();
    initSeatSelection();
    initCheckout();
    initTicketDownload();
});

/* ---------- Helper: format a number as Indian Rupees ---------- */
function formatINR(amount) {
    return "₹" + new Intl.NumberFormat("en-IN").format(amount);
}

/* =========================================================
   TOAST NOTIFICATIONS
   Flask flash() messages are already in the page.
   From JavaScript use:  showToast("Saved!", "success");
   Types: success, error, warning, info
   ========================================================= */
var TOAST_ICONS = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };

function dismissToast(toast) {
    if (!toast || toast.dataset.closing) return;
    toast.dataset.closing = "true";
    toast.classList.add("hide");
    setTimeout(function () { toast.remove(); }, 350);
}

function armToast(toast) {
    var closeButton = toast.querySelector(".toast-close");
    if (closeButton) {
        closeButton.addEventListener("click", function () { dismissToast(toast); });
    }
    var duration = toast.classList.contains("toast-error") ? 8000 : 5000;
    var bar = toast.querySelector(".toast-progress");
    if (bar) bar.style.animationDuration = duration + "ms";
    setTimeout(function () { dismissToast(toast); }, duration);
}

function showToast(message, type) {
    var container = document.getElementById("toast-container");
    if (!container) return;
    type = type || "info";

    // Do not show the same message twice at the same time
    var existing = container.querySelectorAll(".toast-body");
    for (var i = 0; i < existing.length; i++) {
        if (existing[i].textContent === message) return;
    }

    var toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    toast.setAttribute("role", "alert");

    var icon = document.createElement("span");
    icon.className = "toast-icon";
    icon.textContent = TOAST_ICONS[type] || TOAST_ICONS.info;

    var body = document.createElement("div");
    body.className = "toast-body";
    body.textContent = message;

    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close";
    close.setAttribute("aria-label", "Close");
    close.innerHTML = "&times;";

    var bar = document.createElement("span");
    bar.className = "toast-progress";

    toast.appendChild(icon);
    toast.appendChild(body);
    toast.appendChild(close);
    toast.appendChild(bar);
    container.appendChild(toast);
    armToast(toast);
}

function initToasts() {
    document.querySelectorAll("#toast-container .toast").forEach(armToast);
}

/* ---------- Navbar: mobile menu, user dropdown, shadow on scroll ---------- */
function initNavbar() {
    var navbar = document.getElementById("navbar");
    var toggle = document.getElementById("nav-toggle");
    var links = document.getElementById("nav-links");
    var userMenu = document.getElementById("user-menu");
    var userBtn = document.getElementById("user-btn");

    if (toggle && links) {
        toggle.addEventListener("click", function () {
            links.classList.toggle("open");
            toggle.textContent = links.classList.contains("open") ? "✕" : "☰";
        });
    }

    if (userMenu && userBtn) {
        userBtn.addEventListener("click", function (event) {
            event.stopPropagation();
            userMenu.classList.toggle("open");
        });
        document.addEventListener("click", function (event) {
            if (!userMenu.contains(event.target)) {
                userMenu.classList.remove("open");
            }
        });
    }

    if (navbar) {
        var onScroll = function () {
            navbar.classList.toggle("scrolled", window.scrollY > 10);
        };
        window.addEventListener("scroll", onScroll);
        onScroll();
    }
}

/* ---------- Reveal elements when they scroll into view ---------- */
function initScrollReveal() {
    var items = document.querySelectorAll(".reveal");
    if (!items.length) return;

    if (!("IntersectionObserver" in window)) {
        items.forEach(function (item) { item.classList.add("visible"); });
        return;
    }

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    items.forEach(function (item, index) {
        item.style.transitionDelay = (index % 6) * 0.06 + "s";
        observer.observe(item);
    });
}

/* ---------- Animated number counters (hero statistics) ---------- */
function initCounters() {
    var counters = document.querySelectorAll("[data-count]");
    if (!counters.length) return;

    function animate(element) {
        var target = parseInt(element.dataset.count, 10) || 0;
        var suffix = element.dataset.suffix || "";
        var duration = 1400;
        var startTime = null;

        function step(timestamp) {
            if (startTime === null) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            element.textContent = Math.floor(target * eased) + suffix;
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = target + suffix;
            }
        }
        requestAnimationFrame(step);
    }

    if (!("IntersectionObserver" in window)) {
        counters.forEach(animate);
        return;
    }

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                animate(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(function (counter) { observer.observe(counter); });
}

/* ---------- Show / hide password buttons ---------- */
function initPasswordToggle() {
    document.querySelectorAll(".toggle-password").forEach(function (button) {
        button.addEventListener("click", function () {
            var input = document.getElementById(button.dataset.target);
            if (!input) return;
            var show = input.type === "password";
            input.type = show ? "text" : "password";
            button.textContent = show ? "🙈" : "👁️";
        });
    });
}

/* ---------- Password strength meter (register page) ---------- */
function initPasswordStrength() {
    var input = document.querySelector("input[data-strong-password]");
    var meter = document.getElementById("strength");
    var text = document.getElementById("strength-text");
    if (!input || !meter || !text) return;

    var labels = [
        "Use 8+ characters with a letter and a number.",
        "Weak password",
        "Fair password",
        "Good password",
        "Strong password"
    ];

    input.addEventListener("input", function () {
        var value = input.value;
        var score = 0;
        if (value.length >= 8) score++;
        if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
        if (/\d/.test(value)) score++;
        if (/[^A-Za-z0-9]/.test(value)) score++;

        if (value.length > 0 && score === 0) score = 1;
        if (value.length > 0 && value.length < 8) score = 1;   // too short is always weak
        if (value.length === 0) score = 0;

        meter.dataset.level = score;
        text.textContent = labels[score];
    });
}

/* =========================================================
   FORM VALIDATION
   Works automatically on login, register and admin forms.
   Rules come from the HTML attributes: required, type="email",
   minlength, min, max, plus data-match, data-strong-password
   and data-no-digits. Errors appear under each field.
   ========================================================= */
function fieldLabel(input) {
    var label = input.id ? document.querySelector('label[for="' + input.id + '"]') : null;
    if (!label) return "This field";
    return label.textContent.replace(/\(.*?\)/g, "").trim();
}

function getFieldError(input) {
    var label = fieldLabel(input);
    var value = input.value;

    if (input.required && value.trim() === "") return label + " is required.";
    if (value === "") return "";

    if (input.type === "email" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())) {
        return "Please enter a valid email address.";
    }
    if (input.type === "url" && !/^https?:\/\/\S+$/i.test(value.trim())) {
        return "Please enter a link starting with http:// or https://";
    }

    var minLength = parseInt(input.getAttribute("minlength"), 10);
    if (minLength && value.length < minLength) {
        return label + " must be at least " + minLength + " characters.";
    }

    if (input.type === "number") {
        var number = parseFloat(value);
        if (isNaN(number)) return "Please enter a number.";
        if (input.min !== "" && number < parseFloat(input.min)) return label + " must be at least " + input.min + ".";
        if (input.max !== "" && number > parseFloat(input.max)) return label + " must be at most " + input.max + ".";
    }

    if (input.hasAttribute("data-no-digits") && /\d/.test(value)) {
        return label + " cannot contain numbers.";
    }

    if (input.hasAttribute("data-strong-password")) {
        if (value.length < 8 || !/[A-Za-z]/.test(value) || !/\d/.test(value)) {
            return "Use at least 8 characters with a letter and a number.";
        }
    }

    if (input.dataset.match) {
        var other = document.getElementById(input.dataset.match);
        if (other && other.value !== value) return "Passwords do not match.";
    }

    return "";
}

function showFieldError(input, message) {
    var host = input.closest(".input-wrap") || input;
    var error = host.parentNode.querySelector('.field-error[data-for="' + input.name + '"]');

    if (!message) {
        if (error) error.remove();
        input.classList.remove("is-invalid");
        input.removeAttribute("aria-invalid");
        input.classList.toggle("is-valid", input.value.trim() !== "");
        return;
    }

    if (!error) {
        error = document.createElement("p");
        error.className = "field-error";
        error.dataset.for = input.name;
        host.insertAdjacentElement("afterend", error);
    }
    error.textContent = message;
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
    input.setAttribute("aria-invalid", "true");
}

function validateField(field) {
    var message = getFieldError(field);
    showFieldError(field, message);
    return message === "";
}

function initFormValidation() {
    var forms = document.querySelectorAll("form[data-validate], .auth-card form, .card-panel form");

    forms.forEach(function (form) {
        if (form.id === "payment-form") return;   // checkout has its own rules
        form.noValidate = true;                   // we show our own messages

        var fields = form.querySelectorAll("input.form-control, select.form-control, textarea.form-control");

        fields.forEach(function (field) {
            field.addEventListener("blur", function () {
                field.dataset.touched = "true";
                validateField(field);
            });
            field.addEventListener("input", function () {
                if (field.dataset.touched) validateField(field);
                // e.g. re-check "confirm password" when the password changes
                if (field.id) {
                    form.querySelectorAll('[data-match="' + field.id + '"]').forEach(function (dependent) {
                        if (dependent.dataset.touched) validateField(dependent);
                    });
                }
            });
            field.addEventListener("change", function () {
                if (field.dataset.touched) validateField(field);
            });
        });

        form.addEventListener("submit", function (event) {
            var firstInvalid = null;
            fields.forEach(function (field) {
                if (field.disabled) return;
                field.dataset.touched = "true";
                if (!validateField(field) && !firstInvalid) firstInvalid = field;
            });
            if (firstInvalid) {
                event.preventDefault();
                firstInvalid.focus();
                showToast("Please fix the highlighted fields.", "error");
            }
        });
    });
}

/* ---------- Ask for confirmation before risky forms (e.g. delete) ---------- */
function initConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
}

/* ---------- Print button (digital ticket) ---------- */
function initPrintButtons() {
    document.querySelectorAll("[data-print]").forEach(function (button) {
        button.addEventListener("click", function () {
            window.print();
        });
    });
}

/* ---------- Click to copy (booking ID, ticket link) ---------- */
function copyText(text, done) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done);
        return;
    }
    // Fallback for plain http:// pages
    var box = document.createElement("textarea");
    box.value = text;
    box.style.position = "fixed";
    box.style.opacity = "0";
    document.body.appendChild(box);
    box.select();
    try { document.execCommand("copy"); done(); } catch (error) { showToast("Could not copy. Please copy it manually.", "error"); }
    box.remove();
}

function initCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach(function (element) {
        element.addEventListener("click", function () {
            copyText(element.dataset.copy, function () {
                showToast(element.dataset.copyMessage || "Copied to clipboard: " + element.dataset.copy, "success");
            });
        });
    });
}

/* ---------- Auto-submit filter forms when a dropdown changes ---------- */
function initAutoSubmit() {
    document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
        select.addEventListener("change", function () {
            if (select.form) select.form.submit();
        });
    });
}

/* ---------- Countdown timer to an event ---------- */
function initCountdown() {
    var box = document.querySelector("[data-countdown]");
    if (!box) return;

    var target = new Date(box.dataset.countdown).getTime();
    if (isNaN(target)) return;

    function setUnit(unit, value) {
        var element = box.querySelector('[data-unit="' + unit + '"]');
        if (element) element.textContent = String(value).padStart(2, "0");
    }

    function update() {
        var diff = Math.max(target - Date.now(), 0);
        setUnit("days", Math.floor(diff / 86400000));
        setUnit("hours", Math.floor((diff % 86400000) / 3600000));
        setUnit("minutes", Math.floor((diff % 3600000) / 60000));
        setUnit("seconds", Math.floor((diff % 60000) / 1000));
    }

    update();
    setInterval(update, 1000);
}

/* ---------- Tabs (My Bookings: Upcoming / Past) ---------- */
function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (group) {
        var buttons = group.querySelectorAll("[data-tab]");
        var panels = group.querySelectorAll("[data-panel]");

        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                buttons.forEach(function (other) {
                    other.classList.toggle("active", other === button);
                });
                panels.forEach(function (panel) {
                    panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab);
                });
            });
        });
    });
}

/* =========================================================
   INTERACTIVE SEAT SELECTION + LIVE PRICE CALCULATION
   Every seat button carries its own price (data-price), so
   the browser adds them up instantly. The server repeats the
   same calculation before saving, so prices always match.
   ========================================================= */
function initSeatSelection() {
    var map = document.getElementById("seat-map");
    if (!map) return;

    var maxSeats = parseInt(map.dataset.max, 10) || 6;
    var feeRate = parseFloat(map.dataset.feeRate) || 0;
    var selected = [];
    var seatButtons = {};

    var chips = document.getElementById("seat-chips");
    var countEl = document.getElementById("seat-count");
    var breakdown = document.getElementById("seat-breakdown");
    var subtotalEl = document.getElementById("seat-subtotal");
    var feeEl = document.getElementById("seat-fee");
    var totalEl = document.getElementById("seat-total");
    var input = document.getElementById("seats-input");
    var continueButton = document.getElementById("continue-btn");
    var clearButton = document.getElementById("clear-seats");
    var barCount = document.getElementById("bar-count");
    var barTotal = document.getElementById("bar-total");
    var barButton = document.getElementById("bar-btn");

    map.querySelectorAll(".seat[data-seat]").forEach(function (button) {
        seatButtons[button.dataset.seat] = button;
    });

    function sortSeats(list) {
        return list.sort(function (a, b) {
            if (a.charAt(0) !== b.charAt(0)) return a.charAt(0) < b.charAt(0) ? -1 : 1;
            return parseInt(a.slice(1), 10) - parseInt(b.slice(1), 10);
        });
    }

    function setSelected(id, on) {
        var button = seatButtons[id];
        if (!button) return;
        button.classList.toggle("selected", on);
        button.setAttribute("aria-pressed", on ? "true" : "false");
    }

    function makeLine(leftText, rightText) {
        var line = document.createElement("div");
        line.className = "summary-line";
        var left = document.createElement("span");
        left.textContent = leftText;
        var right = document.createElement("strong");
        right.textContent = rightText;
        line.appendChild(left);
        line.appendChild(right);
        return line;
    }

    function update() {
        sortSeats(selected);

        // 1. Add up the price of every selected seat, grouped by category
        var subtotal = 0;
        var groups = {};
        var order = [];
        selected.forEach(function (id) {
            var button = seatButtons[id];
            var price = parseInt(button.dataset.price, 10) || 0;
            var name = button.dataset.tierLabel;
            subtotal += price;
            if (!groups[name]) {
                groups[name] = { count: 0, price: price, amount: 0 };
                order.push(name);
            }
            groups[name].count += 1;
            groups[name].amount += price;
        });

        // 2. Fee and total (Math.round matches the Python calculation)
        var fee = Math.round(subtotal * feeRate);
        var total = subtotal + fee;
        var count = selected.length;

        // 3. Show everything on the page
        if (chips) {
            chips.innerHTML = "";
            if (count === 0) {
                chips.innerHTML = '<span class="muted">No seats selected yet</span>';
            } else {
                selected.forEach(function (id) {
                    var chip = document.createElement("button");
                    chip.type = "button";
                    chip.className = "seat-chip";
                    chip.textContent = id + " ✕";
                    chip.title = "Remove seat " + id;
                    chip.addEventListener("click", function () { toggleSeat(id); });
                    chips.appendChild(chip);
                });
            }
        }

        if (breakdown) {
            breakdown.innerHTML = "";
            order.forEach(function (name) {
                var group = groups[name];
                breakdown.appendChild(makeLine(
                    name + " × " + group.count + " (" + formatINR(group.price) + " each)",
                    formatINR(group.amount)
                ));
            });
        }

        if (countEl) countEl.textContent = count;
        if (subtotalEl) subtotalEl.textContent = formatINR(subtotal);
        if (feeEl) feeEl.textContent = formatINR(fee);
        if (totalEl) totalEl.textContent = formatINR(total);
        if (input) input.value = selected.join(",");

        if (continueButton) continueButton.disabled = count === 0;
        if (clearButton) clearButton.disabled = count === 0;
        if (barButton) barButton.disabled = count === 0;
        if (barCount) barCount.textContent = count + (count === 1 ? " seat" : " seats");
        if (barTotal) barTotal.textContent = formatINR(total);
    }

    function toggleSeat(id) {
        var button = seatButtons[id];
        if (!button || button.classList.contains("taken")) return;

        var position = selected.indexOf(id);
        if (position > -1) {
            selected.splice(position, 1);
            setSelected(id, false);
        } else {
            if (selected.length >= maxSeats) {
                showToast("You can select up to " + maxSeats + " seats at a time.", "warning");
                return;
            }
            selected.push(id);
            setSelected(id, true);
        }
        update();
    }

    function clearSelection() {
        selected.forEach(function (id) { setSelected(id, false); });
        selected = [];
    }

    // Find the best block of "qty" free seats side by side in one row
    function findBlock(seats, qty) {
        var best = null;
        var bestDistance = Infinity;
        var centre = (seats.length - 1) / 2;

        for (var start = 0; start + qty <= seats.length; start++) {
            var block = seats.slice(start, start + qty);
            var allFree = block.every(function (seat) { return !seat.classList.contains("taken"); });
            if (!allFree) continue;
            var distance = Math.abs(start + (qty - 1) / 2 - centre);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = block;
            }
        }
        return best;
    }

    // Quick pick: choose seats together. VIP rows are used only if nothing else is free.
    function quickPick(qty) {
        qty = Math.min(qty, maxSeats);
        var rows = Array.prototype.slice.call(map.querySelectorAll(".seat-row"));
        var ordered = rows.filter(function (row) { return row.dataset.tier !== "vip"; })
            .concat(rows.filter(function (row) { return row.dataset.tier === "vip"; }));

        for (var i = 0; i < ordered.length; i++) {
            var seats = Array.prototype.slice.call(ordered[i].querySelectorAll(".seat"));
            var block = findBlock(seats, qty);
            if (block) {
                clearSelection();
                block.forEach(function (seat) {
                    selected.push(seat.dataset.seat);
                    setSelected(seat.dataset.seat, true);
                });
                update();
                showToast(qty + (qty === 1 ? " seat" : " seats") + " picked for you. You can still change them.", "success");
                return;
            }
        }
        showToast("Could not find " + qty + " seats together. Try fewer seats.", "warning");
    }

    map.addEventListener("click", function (event) {
        var seat = event.target.closest(".seat");
        if (seat && seat.dataset.seat) toggleSeat(seat.dataset.seat);
    });

    document.querySelectorAll(".quick-pick").forEach(function (button) {
        button.addEventListener("click", function () {
            quickPick(parseInt(button.dataset.qty, 10) || 1);
        });
    });

    if (clearButton) {
        clearButton.addEventListener("click", function () {
            clearSelection();
            update();
        });
    }

    update();
}

/* =========================================================
   CHECKOUT: payment tabs, input formatting, validation,
   fake processing screen
   ========================================================= */
function luhnCheck(number) {
    var sum = 0;
    var double = false;
    for (var i = number.length - 1; i >= 0; i--) {
        var digit = parseInt(number.charAt(i), 10);
        if (double) {
            digit *= 2;
            if (digit > 9) digit -= 9;
        }
        sum += digit;
        double = !double;
    }
    return sum % 10 === 0;
}

// For each payment method: a list of [field name, function that returns an error message]
var PAYMENT_RULES = {
    card: [
        ["card_number", function (value) {
            var digits = value.replace(/\s/g, "");
            if (!/^\d{16}$/.test(digits)) return "Enter a valid 16-digit card number.";
            if (!luhnCheck(digits)) return "This card number is not valid. Please check it.";
            return "";
        }],
        ["card_name", function (value) {
            return value.trim().length < 2 ? "Enter the name printed on your card." : "";
        }],
        ["card_expiry", function (value) {
            var match = /^(0[1-9]|1[0-2])\/(\d{2})$/.exec(value);
            if (!match) return "Enter the expiry date as MM/YY.";
            var month = parseInt(match[1], 10);
            var year = 2000 + parseInt(match[2], 10);
            var now = new Date();
            if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) {
                return "This card has expired.";
            }
            return "";
        }],
        ["card_cvv", function (value) {
            return /^\d{3}$/.test(value) ? "" : "Enter the 3-digit CVV.";
        }]
    ],
    upi: [
        ["upi_id", function (value) {
            return /^[\w.\-]{2,}@[A-Za-z]{2,}$/.test(value.trim()) ? "" : "Enter a valid UPI ID like name@bank.";
        }]
    ],
    netbanking: [
        ["bank", function (value) {
            return value ? "" : "Please select your bank.";
        }]
    ]
};

// Check the fields of one payment method. Returns the first bad field (or null).
function validatePayment(form, method) {
    var rules = PAYMENT_RULES[method] || [];
    var firstInvalid = null;

    rules.forEach(function (rule) {
        var field = form.elements[rule[0]];
        if (!field) return;
        var message = rule[1](field.value);
        showFieldError(field, message);
        if (message && !firstInvalid) firstInvalid = field;
    });
    return firstInvalid;
}

function initCheckout() {
    var tabs = document.querySelectorAll(".pay-tab");
    if (!tabs.length) return;

    var form = document.getElementById("payment-form");
    var methodInput = document.getElementById("payment-method");
    var panels = document.querySelectorAll(".pay-panel");

    function activate(method) {
        tabs.forEach(function (tab) {
            tab.classList.toggle("active", tab.dataset.method === method);
        });
        panels.forEach(function (panel) {
            panel.classList.toggle("active", panel.id === "panel-" + method);
        });
        if (methodInput) methodInput.value = method;
    }

    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () { activate(tab.dataset.method); });
    });
    activate((methodInput && methodInput.value) || "card");

    // Card number: only digits, grouped as 1234 5678 9012 3456
    var cardNumber = document.getElementById("card_number");
    if (cardNumber) {
        cardNumber.addEventListener("input", function () {
            var digits = cardNumber.value.replace(/\D/g, "").slice(0, 16);
            cardNumber.value = digits.replace(/(.{4})/g, "$1 ").trim();
        });
    }

    // Expiry: MM/YY
    var expiry = document.getElementById("card_expiry");
    if (expiry) {
        expiry.addEventListener("input", function () {
            var digits = expiry.value.replace(/\D/g, "").slice(0, 4);
            expiry.value = digits.length >= 3 ? digits.slice(0, 2) + "/" + digits.slice(2) : digits;
        });
    }

    // CVV: digits only
    var cvv = document.getElementById("card_cvv");
    if (cvv) {
        cvv.addEventListener("input", function () {
            cvv.value = cvv.value.replace(/\D/g, "").slice(0, 3);
        });
    }

    var overlay = document.getElementById("payment-overlay");
    var payButton = document.getElementById("pay-btn");
    if (!form) return;

    // Once a field has been checked, re-check it while the user types
    form.querySelectorAll(".form-control").forEach(function (field) {
        field.addEventListener("input", function () {
            if (field.classList.contains("is-invalid")) validatePayment(form, methodInput.value);
        });
    });

    form.addEventListener("submit", function (event) {
        if (form.dataset.processing === "true") return;
        event.preventDefault();

        var badField = validatePayment(form, methodInput.value);
        if (badField) {
            badField.focus();
            showToast("Please check your payment details.", "error");
            return;
        }

        form.dataset.processing = "true";
        if (payButton) {
            payButton.disabled = true;
            payButton.textContent = "Processing…";
        }
        if (overlay) overlay.classList.add("show");

        setTimeout(function () {
            form.submit();   // submit() does not trigger this handler again
        }, 1800);
    });
}

/* ---------- Download the ticket as a PNG image ---------- */
function initTicketDownload() {
    var button = document.querySelector("[data-download-ticket]");
    var ticket = document.getElementById("ticket-card");
    if (!button || !ticket) return;

    button.addEventListener("click", function () {
        if (typeof window.html2canvas === "undefined") {
            showToast("The download tool could not load. Use Print and choose 'Save as PDF' instead.", "warning");
            return;
        }

        var originalText = button.textContent;
        button.disabled = true;
        button.textContent = "Preparing…";

        window.html2canvas(ticket, {
            scale: 2,
            backgroundColor: null,
            useCORS: true,
            scrollX: 0,
            scrollY: -window.scrollY
        }).then(function (canvas) {
            var link = document.createElement("a");
            link.download = (button.dataset.filename || "eventease-ticket") + ".png";
            link.href = canvas.toDataURL("image/png");
            document.body.appendChild(link);
            link.click();
            link.remove();
            showToast("Your ticket was downloaded as an image.", "success");
        }).catch(function () {
            showToast("Could not create the image. Please use Print → Save as PDF.", "error");
        }).then(function () {
            button.disabled = false;
            button.textContent = originalText;
        });
    });
}