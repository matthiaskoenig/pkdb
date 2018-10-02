<template>
    <div id="footer">
        <p class="small alert-info">&copy; 2017-2018 PK-DB &nbsp;&nbsp;
            Website: <a :href="web" target="_blank">{{web}}</a> &nbsp;&nbsp;
            Email: <a :href="'mailto:'+email" target="_blank">{{email}}</a> &nbsp;&nbsp;
        </p>

    </div>
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
<style>
    #footer {
        margin-top: 20px;
        margin-bottom: 20px;
    }
</style>