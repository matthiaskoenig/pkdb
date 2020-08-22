<template>
    <v-footer id="footer">
        <span>&copy; 2017-2020 PK-DB <a :href="web" target="_blank">{{ web }}</a>
        </span>
    </v-footer>
</template>

<script>
    export default {
        name: 'Footer',
        data() {
            return {
                web: 'https://livermetabolism.com',
            }
        }
    }
</script>

<style>
</style>