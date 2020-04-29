<template>
    <span v-if="resource_url">
        <v-btn slot="activator" fab dark small text color="black" :href="resource_url"
               :disabled="resource_url ? false : true" title="Extern JSON">
            <v-icon dark>fas fa-file-export</v-icon>
        </v-btn>
    </span>
</template>

<script>
    export default {
        name: "ExportFormatButton",
        props: {
            resource_url: String
        }
    }
</script>

<style scoped>

</style>