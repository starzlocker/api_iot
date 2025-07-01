s = ['abcba', 'abccba', 'abcde', 'a', 'aa', 'aba'];

function isPalindrome(s) {
	for (const item of s) {
		for (let i = s.length - 1, j = 0; j < s.length / 2; i--, j++) {
			if (s[i] !== s[j]) {
				console.log('false')
				return false;
			}
			console.log('next')
		}	
	}
	return true;
}

console.log(isPalindrome(s)); 
