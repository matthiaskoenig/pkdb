<template>
    <span>
        <template slot="no-data">
            <v-alert :value="true" color="warning" icon="fas fa-exclamation">
                Sorry, nothing to display here :(
            </v-alert>
        </template>
    </span>
</template>

<script>
    export default {
        name: "NoData"
    }
</script>

<style scoped>

</style>