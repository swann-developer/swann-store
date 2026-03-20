document.addEventListener('DOMContentLoaded', () => {
   // CATEGORY SCROLL
   const scrollContainer = document.getElementById('categoryScroll');
   const nextBtn = document.getElementById('nextBtn');
   const prevBtn = document.getElementById('prevBtn');

   const scrollAmount = 250;

   if (scrollContainer && nextBtn && prevBtn) {
      nextBtn.addEventListener('click', () => {
         scrollContainer.scrollLeft += scrollAmount;
      });

      prevBtn.addEventListener('click', () => {
         scrollContainer.scrollLeft -= scrollAmount;
      });
   }

   // ADD TO CART QTY
   const minusBtn = document.getElementById('minus');
   const plusBtn = document.getElementById('plus');
   const qtyEl = document.getElementById('qty');

   let qty = 1;
   const min = 1;
   const max = 10;

   if (minusBtn && plusBtn && qtyEl) {
      function updateQty() {
         qtyEl.textContent = qty;
         minusBtn.disabled = qty <= min;
         plusBtn.disabled = qty >= max;
      }

      minusBtn.addEventListener('click', () => {
         if (qty > min) {
            qty--;
            updateQty();
         }
      });

      plusBtn.addEventListener('click', () => {
         if (qty < max) {
            qty++;
            updateQty();
         }
      });

      updateQty();
   }
});

/// billing details (safe)
const checkbox = document.getElementById('createAccountCheckbox');
const section = document.getElementById('createAccountSection');

if (checkbox && section) {
  checkbox.addEventListener('change', () => {
    if (checkbox.checked) {
      section.classList.remove('d-none');
    } else {
      section.classList.add('d-none');
    }
  });
}

// ===============================
// PRODUCT IMAGE SWITCHER
// ===============================
document.addEventListener("DOMContentLoaded", function () {
  const mainImage = document.getElementById("mainImage");
  const thumbs = document.querySelectorAll(".thumb");

  if (!mainImage || thumbs.length === 0) return;

  thumbs.forEach((thumb) => {
    thumb.addEventListener("click", function () {
      const newSrc = this.getAttribute("data-image");
      if (!newSrc) return;

      mainImage.src = newSrc;
      mainImage.srcset = newSrc;

      thumbs.forEach((t) => t.classList.remove("active"));
      this.classList.add("active");
    });
  });
});

// ===============================
// IMAGE HOVER ZOOM
// ===============================
document.addEventListener("DOMContentLoaded", function () {
  const mainImage = document.getElementById("mainImage");
  const zoomResult = document.getElementById("zoomResult");

  if (!mainImage || !zoomResult) return;

  function activateZoom(imgSrc) {
    zoomResult.style.backgroundImage = `url('${imgSrc}')`;
  }

  // initial zoom image
  activateZoom(mainImage.src);

  // mouse move zoom
  mainImage.addEventListener("mousemove", function (e) {
    const rect = mainImage.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    zoomResult.style.display = "block";
    zoomResult.style.backgroundPosition = `${x}% ${y}%`;
    zoomResult.style.backgroundSize = "200%";
  });

  mainImage.addEventListener("mouseleave", function () {
    zoomResult.style.display = "none";
  });

  // 🔥 keep zoom synced when thumbnail changes
  document.querySelectorAll(".thumb").forEach((thumb) => {
    thumb.addEventListener("click", function () {
      const zoomSrc =
        this.getAttribute("data-zoom-image") ||
        this.getAttribute("data-image");

      activateZoom(zoomSrc);
    });
  });
});

// ===============================
// THUMBNAIL SCROLL ARROWS
// ===============================
document.addEventListener("DOMContentLoaded", function () {
  const thumbList = document.getElementById("thumbList");
  const nextBtn = document.getElementById("thumbNext");
  const prevBtn = document.getElementById("thumbPrev");

  if (!thumbList || !nextBtn || !prevBtn) return;

  const scrollAmount = 200;

  nextBtn.addEventListener("click", () => {
    thumbList.scrollLeft += scrollAmount;
  });

  prevBtn.addEventListener("click", () => {
    thumbList.scrollLeft -= scrollAmount;
  });
});



// size → variant mapping + stock check
const sizeSelect = document.getElementById("sizeSelect");
const variantInput = document.getElementById("variantInput");
const addBtn = document.getElementById("addToCartBtn");
const buyNowBtn = document.getElementById("buyNowBtn");

if (sizeSelect && variantInput) {

  sizeSelect.addEventListener("change", function () {

    variantInput.value = this.value;

    const selected = this.options[this.selectedIndex];
    const stock = parseInt(selected.dataset.stock || 0);

    if(stock === 0){

      if(addBtn){
        addBtn.disabled = true;
        addBtn.innerText = "Out of Stock";
      }

      if(buyNowBtn){
        buyNowBtn.disabled = true;
      }

    }else{

      if(addBtn){
        addBtn.disabled = false;
        addBtn.innerText = "Add to Cart";
      }

      if(buyNowBtn){
        buyNowBtn.disabled = false;
      }

    }

  });

}

// =============================
// CART LIVE CALCULATIONS
// =============================
document.addEventListener("DOMContentLoaded", function () {
  function recalcCart() {
  let subtotalMRP = 0;
  let finalTotal = 0;
  let totalDiscount = 0;

  document.querySelectorAll(".cart-card").forEach((card) => {
    const qtyEl = card.querySelector(".qty-value");
    const priceEl = card.querySelector(".item-cart-price");
    const wrapper = card.querySelector(".qty-wrapper");

    if (!qtyEl || !priceEl || !wrapper) return;

    const qty = parseInt(qtyEl.textContent) || 1;

    // ✅ SAFE READ
    const mrp = parseFloat(wrapper.dataset.mrpPrice || 0);
    const finalPrice = parseFloat(wrapper.dataset.finalPrice || wrapper.dataset.price || 0);

    const lineFinal = finalPrice * qty;
    const lineMRP = mrp * qty;
    const lineDiscount = lineMRP - lineFinal;

    subtotalMRP += lineMRP;
    finalTotal += lineFinal;
    totalDiscount += lineDiscount;

    priceEl.textContent = "AED " + lineFinal.toFixed(2);
  });

  const subtotalEl = document.getElementById("cartSubtotal");
  const totalEl = document.getElementById("cartTotal");
  const discountEl = document.getElementById("cartDiscount");
  const savedPercentEl = document.getElementById("cartSavedPercent");

  if (subtotalEl) subtotalEl.textContent = "AED " + subtotalMRP.toFixed(2);
  if (totalEl) totalEl.textContent = "AED " + finalTotal.toFixed(2);
  if (discountEl) discountEl.textContent = "AED " + totalDiscount.toFixed(2);

  let percent = 0;
  if (subtotalMRP > 0) {
    percent = (totalDiscount / subtotalMRP) * 100;
  }

  if (savedPercentEl) savedPercentEl.textContent = percent.toFixed(2);
}

  // PLUS / MINUS
  document.querySelectorAll(".cart-card").forEach((card) => {
    const minus = card.querySelector(".qty-minus");
    const plus = card.querySelector(".qty-plus");
    const qtyEl = card.querySelector(".qty-value");

    if (!minus || !plus || !qtyEl) return;

    let qty = parseInt(qtyEl.textContent) || 1;
    const MIN = 1;
    const MAX = 10;

    minus.addEventListener("click", () => {
      if (qty > MIN) {
        qty--;
        qtyEl.textContent = qty;

const itemId = card.dataset.itemId;

fetch(`/cart/update/${itemId}/`,{
method:"POST",
headers:{
"Content-Type":"application/json",
"X-CSRFToken":document.querySelector("[name=csrfmiddlewaretoken]").value
},
body:JSON.stringify({
quantity: qty
})
});

recalcCart();
      }
    });

    plus.addEventListener("click", () => {
      if (qty < MAX) {
        qty++;
        qtyEl.textContent = qty;

const itemId = card.dataset.itemId;

fetch(`/cart/update/${itemId}/`,{
method:"POST",
headers:{
"Content-Type":"application/json",
"X-CSRFToken":document.querySelector("[name=csrfmiddlewaretoken]").value
},
body:JSON.stringify({
quantity: qty
})
});

recalcCart();
      }
    });
  });

  recalcCart();
});
// ===============================
// PRODUCT DETAIL CART LOGIC (FIXED)
// ===============================
document.addEventListener("DOMContentLoaded", function () {

  const form = document.querySelector("form[action='/cart/add/']");
  const addBtn = document.getElementById("addToCartBtn");
  const viewCartBtn = document.getElementById("viewCartBtn");
  const variantInput = document.getElementById("variantInput");
  const errorEl = document.getElementById("variantError");

  if(!form) return;

  form.addEventListener("submit", async function(e){

    e.preventDefault();

    if(!variantInput.value){
      errorEl.classList.remove("d-none");
      return;
    }

    const formData = new FormData(form);

    const response = await fetch("/cart/add/",{
      method:"POST",
      headers:{
        "X-CSRFToken":document.querySelector("[name=csrfmiddlewaretoken]").value
      },
      body:formData
    });

    const data = await response.json();

    if(data.status === "added"){

      addBtn.innerText = "Added to Cart";
      viewCartBtn.classList.remove("d-none");

    }

    else if(data.status === "exists"){

      addBtn.innerText = "Already in Cart";
      viewCartBtn.classList.remove("d-none");

    }

    else if(data.status === "out_of_stock"){

      addBtn.innerText = "Out of Stock";
      addBtn.disabled = true;

    }

  });

});


const sendOtpBtn = document.getElementById("sendOtpBtn");
const phoneInput = document.getElementById("phoneInput");
const otpSection = document.getElementById("otpSection");
const otpInput = document.getElementById("otpInput");
const otpMessage = document.getElementById("otpMessage");
const placeOrderBtn = document.getElementById("placeOrderBtn");
const applyCouponBtn = document.getElementById("applyCouponBtn");
const couponInput = document.getElementById("couponInput");


if(sendOtpBtn){

sendOtpBtn.addEventListener("click", async function(){

const countryCode = document.querySelector("select[name='country_code']").value;
let phoneNumber = phoneInput.value.trim();

if(phoneNumber.startsWith("0")){
    phoneNumber = phoneNumber.substring(1);
}

const phone = countryCode + phoneNumber;

if(!phone){
otpMessage.innerHTML = "<div class='text-danger'>Enter phone number</div>";
return;
}

const response = await fetch("/send-otp/",{
method:"POST",
headers:{
"Content-Type":"application/json",
"X-CSRFToken":document.querySelector("[name=csrfmiddlewaretoken]").value
},
body:JSON.stringify({
  phone: phone
})
});

const data = await response.json();

if(data.status === "wait"){

let timeLeft = 30;

sendOtpBtn.disabled = true;

otpMessage.innerHTML =
"<div class='text-danger'>Please wait <span id='otpTimer'>30</span> seconds to resend OTP</div>";

const timer = setInterval(function(){

timeLeft--;

document.getElementById("otpTimer").innerText = timeLeft;

if(timeLeft <= 0){

clearInterval(timer);

sendOtpBtn.disabled = false;

otpMessage.innerHTML = "";

}

},1000);

return;

}

if(data.status==="sent"){

otpSection.classList.remove("d-none");

otpMessage.innerHTML =
"<div class='text-success'>OTP sent. Please check your phone.</div>";

sendOtpBtn.innerText = "Resend OTP";

}

});
}


const verifyOtpBtn = document.getElementById("verifyOtpBtn");

if(verifyOtpBtn){

verifyOtpBtn.addEventListener("click", async function(){

const otp = otpInput.value.trim();

if(otp.length !== 6){
otpMessage.innerHTML = "<div class='text-danger'>Enter valid OTP</div>";
return;
}

const countryCode = document.querySelector("select[name='country_code']").value;
let phoneNumber = phoneInput.value.trim();

if(phoneNumber.startsWith("0")){
phoneNumber = phoneNumber.substring(1);
}

const phone = countryCode + phoneNumber;

const response = await fetch("/verify-otp/",{
method:"POST",
headers:{
"Content-Type":"application/json",
"X-CSRFToken":document.querySelector("[name=csrfmiddlewaretoken]").value
},
body:JSON.stringify({
otp: otp
})
});

const data = await response.json();

if(data.status === "verified"){

otpMessage.innerHTML =
"<div class='text-success'>Phone verified successfully</div>";

placeOrderBtn.disabled = false;
placeOrderBtn.dataset.disabled = "false";

verifyOtpBtn.disabled = true;
verifyOtpBtn.innerText = "Verified";

}

else{

otpMessage.innerHTML =
"<div class='text-danger'>Invalid OTP</div>";

}

});

}
document.addEventListener("DOMContentLoaded", function () {

  const placeOrderBtn = document.getElementById("placeOrderBtn");
  const otpWarning = document.getElementById("otpWarning");

  if (!placeOrderBtn || !otpWarning) return;

  placeOrderBtn.addEventListener("click", function (e) {

    // if still not verified
    if (placeOrderBtn.dataset.disabled === "true") {
      e.preventDefault();

      otpWarning.classList.remove("d-none");

      // auto hide after 3 sec
      setTimeout(() => {
        otpWarning.classList.add("d-none");
      }, 3000);
    }

  });

});

// ===============================
// NAVBAR SEARCH
// ===============================

document.addEventListener("DOMContentLoaded", function () {

const toggle = document.getElementById("searchToggle");
const box = document.getElementById("searchBox");
const input = document.getElementById("searchInput");
const suggestions = document.getElementById("searchSuggestions");

if(!toggle || !box || !input || !suggestions) return;


// toggle search box
toggle.addEventListener("click", function(e){
e.preventDefault();
box.classList.toggle("d-none");
input.focus();
});


// autosuggestions
input.addEventListener("keyup", function(){

const query = this.value.trim();

if(query.length < 1){
suggestions.innerHTML="";
return;
}

fetch(`/search-suggestions/?q=${encodeURIComponent(query)}`)
.then(res => res.json())
.then(data => {

suggestions.innerHTML="";

data.results.forEach(item => {

const el = document.createElement("a");

el.href = item.url;

el.innerHTML = `
<img src="${item.image}">
<span>${item.title}</span>
`;

suggestions.appendChild(el);

});

});

});


// close if clicking outside
document.addEventListener("click", function(e){

if(!box.contains(e.target) && !toggle.contains(e.target)){
box.classList.add("d-none");
suggestions.innerHTML="";
}

});

// enter key search
input.addEventListener("keypress", function(e){

if(e.key === "Enter"){

const q = input.value.trim();

if(q){
window.location = `/products/?search=${encodeURIComponent(q)}`;
}

}

});

});

// ===============================
// CONTACT FORM AJAX
// ===============================
document.addEventListener("DOMContentLoaded", function () {

const form = document.getElementById("contactForm");
const alertBox = document.getElementById("contactAlert");

if(!form || !alertBox) return;

form.addEventListener("submit", async function(e){

e.preventDefault();

const formData = new FormData(form);

const response = await fetch("/contact/",{
method:"POST",
headers:{
"X-CSRFToken":document.querySelector("[name=csrfmiddlewaretoken]").value
},
body:formData
});

const data = await response.json();

if(data.status === "success"){

alertBox.innerHTML =
"<div class='alert alert-success'>Message sent successfully.</div>";

form.reset();

}

else if(data.status === "blocked"){

alertBox.innerHTML =
"<div class='alert alert-danger'>Too many messages. Please try again later.</div>";

}

else{

alertBox.innerHTML =
"<div class='alert alert-danger'>Please fill all required fields.</div>";

}

});

});
