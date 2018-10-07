<template>
    <div class="individual-info">
    <v-layout>
        <v-flex xs2>
            <span class="attr"> Individual Name</span><br />
            {{ individual.name }}
        </v-flex>
        <v-flex xs6>
            <span class="attr">Group</span><br />
            <get-data :resource_url="individual.group">
                <span slot-scope="group">
                    <group-info :group="group.data" :resource_url="individual.group" />
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