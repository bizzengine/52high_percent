// static/script.js
const stockInput = document.getElementById('stockInput');
const autocompleteDropdown = document.getElementById('autocomplete-dropdown');
const analyzeButton = document.getElementById('analyzeButton');

// 초기 버튼 텍스트를 저장할 변수
let originalButtonText = analyzeButton.textContent;

// 버튼 내부에 텍스트를 감싸는 span을 만들고 스피너 엘리먼트를 추가
if (analyzeButton) {
    const buttonTextSpan = document.createElement('span');
    buttonTextSpan.classList.add('button-text');
    buttonTextSpan.textContent = originalButtonText;
    analyzeButton.innerHTML = ''; // 기존 버튼 내용 비우기
    analyzeButton.appendChild(buttonTextSpan);

    const spinner = document.createElement('div');
    spinner.classList.add('spinner');
    analyzeButton.appendChild(spinner);
}

stockInput.addEventListener('input', function () {
    autocompleteDropdown.innerHTML = '';
    autocompleteDropdown.style.display = 'none';
});

document.addEventListener('click', function (event) {
    if (!stockInput.contains(event.target) && !autocompleteDropdown.contains(event.target)) {
        autocompleteDropdown.style.display = 'none';
    }
});

// "분석하기" 버튼 클릭 시 로딩 상태를 표시하는 함수
function showLoading() {
    if (analyzeButton) {
        analyzeButton.querySelector('.button-text').textContent = '분석 중'; // 텍스트 변경
        analyzeButton.classList.add('loading'); // 로딩 CSS 클래스 추가
        analyzeButton.disabled = true; // 버튼 비활성화 (중복 클릭 방지)
        // 스피너는 CSS 클래스를 통해 표시/숨김 처리됨
    }
}