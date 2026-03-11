const mainImage = document.getElementById('mainImage');
const zoomResult = document.getElementById('zoomResult');
const thumbs = document.querySelectorAll('.thumb');

const zoomLevel = 2.5;

/* Thumbnail click */
thumbs.forEach((thumb) => {
   thumb.addEventListener('click', () => {
      document.querySelector('.thumb.active').classList.remove('active');
      thumb.classList.add('active');
      mainImage.src = thumb.src;
   });
});

/* Hover zoom */
mainImage.addEventListener('mouseenter', () => {
   zoomResult.style.display = 'block';
   zoomResult.style.backgroundImage = `url('${mainImage.src}')`;
   zoomResult.style.backgroundSize =
      mainImage.width * zoomLevel + 'px ' + mainImage.height * zoomLevel + 'px';
});

mainImage.addEventListener('mousemove', (e) => {
   const rect = mainImage.getBoundingClientRect();
   const x = e.clientX - rect.left;
   const y = e.clientY - rect.top;

   zoomResult.style.backgroundPosition = `${(x / mainImage.width) * 100}% ${(y / mainImage.height) * 100}%`;
});

mainImage.addEventListener('mouseleave', () => {
   zoomResult.style.display = 'none';
});

const thumbList = document.getElementById('thumbList');
const prevBtn = document.getElementById('thumbPrev');
const nextBtn = document.getElementById('thumbNext');

const scrollAmount = 150; // px per click

prevBtn.addEventListener('click', () => {
   thumbList.scrollLeft -= scrollAmount;
});

nextBtn.addEventListener('click', () => {
   thumbList.scrollLeft += scrollAmount;
});
