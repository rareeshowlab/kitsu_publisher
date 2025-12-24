import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit()
	],
	server: {
		proxy: {
			'/auth': 'http://localhost:8000',
			'/files': 'http://localhost:8000',
			'/kitsu': 'http://localhost:8000',
			'/publish': 'http://localhost:8000',
			'/logs': 'http://localhost:8000',
			'/system': 'http://localhost:8000'
		}
	}
});
