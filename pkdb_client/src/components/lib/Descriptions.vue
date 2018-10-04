<template>
    <div id="descriptions">
        <md-list>
            <md-list-item v-for="item in descriptions" :key="item"></md-list-item>
        </md-list>
    </div>
</template>

<script>
    export default {
        name: "Descriptions",
        props: {
            descriptions: {
                type: Object,
            }
        }
    }
</script>

<style scoped>

</style>