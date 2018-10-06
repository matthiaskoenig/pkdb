<template>
    <v-layout id="individual-info" row wrap>
        <v-flex>
            <info-text>Name</info-text><br/>
            {{ individual.name }}
        </v-flex>
        <v-flex>
            <info-text>Group</info-text><br/>
            <!--<GetData d
            {{ individual.group }}
            -->
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

</style>