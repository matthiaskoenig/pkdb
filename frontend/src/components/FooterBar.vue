<template>
    <span id="footer-bar">
        <span>&copy; 2017-2020 PK-DB <a :href="web" target="_blank">{{ web }}</a>
        </span>
    </span>
</template>

<script>
    export default {
        name: 'FooterBar',
        data() {
            return {
                web: 'https://livermetabolism.com',
            }
        }
    }
</script>

<style scoped>
</style>