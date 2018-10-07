<template>
    <div class="individual-info">
    <v-layout>
        <v-flex xs2>
            <span class="attr"> Individual Name</span><br />
            {{ individual.name }}
        </v-flex>
        <v-flex xs6>
            <span class="attr">Group</span><br />

            <GetData :resource_url="individual.group">
                <span slot-scope="group">
                    <GroupInfo :group="group.data" :resource_url="individual.group" />
                </span>
            </GetData>

        </v-flex>
    </v-layout>
    </div>

    <v-layout>
        <v-flex xs4>
            <span class="attr">Group Name</span><br />
            {{ group.name }}
        </v-flex>
        <v-flex xs4>
            <span class="attr">Group Size</span><br />
            {{ group.count }}
        </v-flex>
        <v-flex xs4>
            <span class="attr">Group Individuals</span><br />
            <span v-if="(group.individuals && group.individuals.length>0)">
                    <v-icon>fa fa-check-circle</v-icon> {{ group.individuals.length }}"</span>
            <span v-else>
                    <v-icon>fa fa-times-circle</v-icon>
                </span>
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