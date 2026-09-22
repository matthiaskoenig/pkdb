// Keep browser sessions on the same origin in local development.
module.exports = {
    lintOnSave: 'default',
    devServer: {
        proxy: {
            '/api': {target: 'http://127.0.0.1:8000'},
            '/accounts': {target: 'http://127.0.0.1:8000'}
        },
        overlay: {warnings: true, errors: true}
    }
};
