<template>
    <v-footer id="footer">
        <span>&copy; 2017-2020 Pharmacokinetics Database PK-DB &nbsp;&nbsp;
            Website: <a :href="web" target="_blank">{{web}}</a> &nbsp;&nbsp;
            Email: <a :href="'mailto:'+email" target="_blank">{{email}}</a> &nbsp;&nbsp;
        </span>
    </v-footer>
</template>

<script>
    export default {
        name: 'Footer',

        data() {
            return {
                email: 'koenigmx@hu-berlin.de',
                web: 'https://livermetabolism.com',
            }
        }
    }
</script>
<style scoped>
</style>