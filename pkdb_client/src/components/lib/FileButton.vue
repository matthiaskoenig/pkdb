<template>
    <span v-if="resource_url">
        <v-dialog scrollable>
        <v-btn slot="activator" fab dark small flat color="black"
               :disabled="resource_url ? false : true" title="PDF">
            <v-icon dark>fas fa-file</v-icon>
        </v-btn>
            <v-card style="height: 800px;">
                <embed :src="resource_url"  height="100%" width="100%"/>
            </v-card>
    </v-dialog>

    </span>
</template>

<script>
    export default {
        name: "FileButton",
        props: {
            resource_url: String
        }
    }
</script>

<style scoped>

</style>