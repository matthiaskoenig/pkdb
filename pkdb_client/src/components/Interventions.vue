<template>
    <div>
        <md-table  md-height="800px" class="my-table" v-model="entries" v-if="count" md-card>

            <md-table-toolbar>
                <md-badge  class="md-square md-primary" :md-content="count">
                    <h3 class="md-title"  style="flex: 1" ><font-awesome-icon icon="capsules"/>   Interventions  </h3>
                </md-badge>

                <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-raised">
                    <font-awesome-icon icon="code"/>
                </md-button>
            </md-table-toolbar>

            <md-table-row slot="md-table-row" slot-scope="{item}">
                <md-table-cell md-label="Pk"> <font-awesome-icon icon="capsules" /> {{ item.pk }} </md-table-cell>
                <md-table-cell md-label="Name" >{{ item.name }}</md-table-cell>
                <md-table-cell md-label="Category" >{{ item.category }}</md-table-cell>
                <md-table-cell md-label="Choice">{{ item.choice }}</md-table-cell>
                <md-table-cell md-label="Route">{{ item.route }}</md-table-cell>
                <md-table-cell md-label="Form">{{item.form}}</md-table-cell>
                <md-table-cell md-label="Application">{{item.application}}</md-table-cell>
                <md-table-cell md-label="Substance"><a v-if="item.substance" :href="item.substance" :title="item.substance"><font-awesome-icon icon="tablets" /></a></md-table-cell>
                <md-table-cell md-label="Time"> {{item.time}} </md-table-cell>
                <md-table-cell md-label="Time Unit"> {{ item.time_unit }} </md-table-cell>
                <md-table-cell md-label="Unit"> {{item.unit}} </md-table-cell>
                <md-table-cell md-label="Value"> {{ item.value }} </md-table-cell>
                <md-table-cell md-label="Mean"> {{ item.mean }}</md-table-cell>
                <md-table-cell md-label="Median"> {{ item.median }}</md-table-cell>
                <md-table-cell md-label="Min">{{ item.min }}</md-table-cell>
                <md-table-cell md-label="Max">{{ item.max }}</md-table-cell>
                <md-table-cell md-label="Sd">{{ item.sd }}</md-table-cell>
                <md-table-cell md-label="Se">{{ item.se }}</md-table-cell>
                <md-table-cell md-label="Cv">{{ item.cv }}</md-table-cell>

            </md-table-row>
        </md-table>
        <v-paginator :resource_url="resource_url" @update="updateResource"></v-paginator>
    </div>
</template>
<script>
import VuePaginator from '@/components/VPaginator';
export default {
    name: 'Interventions',
    components: {
        VPaginator: VuePaginator
    },
    props: {
        api: String
    },
    methods:{
        updateResource(data){
            this.entries = data.data;
            this.count = data.count
        }
    },
    data() {
        return {
            entries: [],
            count: null,
            resource_url: this.api + '/interventions_read/?format=json&final=True',
            }
        }
}
</script>
<style>

</style>