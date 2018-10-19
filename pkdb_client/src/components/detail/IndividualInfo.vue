<template>
    <div class="individual-info">
    <v-layout>
        <v-flex>
            <div class="attr-card">
            <span class="attr"> Individual Name</span><br />
            {{ individual.name }}
            </div>
        </v-flex>
        <v-flex>
            <get-data :resource_url="individual.group.url">
                <span slot-scope="group">
                    <group-info :group="group.data" :resource_url="individual.group.url" />
                </span>
            </get-data>
        </v-flex>
    </v-layout>
    </div>
</template>

<script>
    export default {
        name: "IndividualInfo",
        props: {
            individual: {
                type: Object,
                required: true,
            }
        }
    }
</script>

<style scoped>

</style>