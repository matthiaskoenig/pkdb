<template>
    <v-layout id="individual-info" row wrap>
        <v-flex>
            <info-text>Name</info-text><br/>
            {{ individual.name }}
        </v-flex>
        <v-flex>
            <info-text>Group</info-text><br/>
            <GetData :resource_url="individual.group">
                <span slot-scope="group">
                    <GroupInfo :group="group.data" :resource_url="individual.group" />
                </span>
            </GetData>
        </v-flex>
    </v-layout>
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
    .v-card{
        padding: 0px;
    }
</style>