<template>
    <div class="json-button">
    <span v-if="resource_url">

    <!--<v-dialog v-model="dialog" width="80%"> -->

            <v-btn slot="activator" fab dark small color="green" :href="resource_url"
                   :disabled="resource_url ? false : true" title="JSON">
                <v-icon dark>fas fa-code</v-icon>
            </v-btn>

        <!--
        <v-card>
            <v-card-title
                    class="headline grey lighten-2"
                    primary-title
            >
                JSON (REST API)
            </v-card-title>

            <v-card-text>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
            </v-card-text>

            <v-divider></v-divider>

            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                        color="primary"
                        flat
                        @click="dialog = false"
                >
                    I accept
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
    -->


    </span>
    </div>
</template>

<script>
    export default {
        name: "JsonButton",
        props: {
            resource_url: String
        }
    }
</script>

<style scoped>

</style>