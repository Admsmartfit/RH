module.exports = {
	root: true,
	env: { browser: true, es2022: true, node: true },
	parserOptions: { ecmaVersion: "latest", sourceType: "module" },
	extends: ["eslint:recommended", "plugin:vue/vue3-recommended"],
	rules: {
		// o código segue a indentação com tabs do projeto; o formatador não é o ESLint
		"vue/html-indent": ["error", "tab"],
		"vue/max-attributes-per-line": "off",
		"vue/singleline-html-element-content-newline": "off",
		"vue/multi-word-component-names": "off",
		"vue/html-self-closing": "off",
	},
};
