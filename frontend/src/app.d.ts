interface PywebviewApi {
	select_folder: () => Promise<string | null>;
	save_session: (tokens: any, host: string) => Promise<boolean>;
	get_session: () => Promise<any>;
	clear_session: () => Promise<boolean>;
	save_setting: (key: string, value: any) => Promise<boolean>;
	get_setting: (key: string) => Promise<any>;
}

interface Window {
	pywebview: {
		api: PywebviewApi;
	};
}
