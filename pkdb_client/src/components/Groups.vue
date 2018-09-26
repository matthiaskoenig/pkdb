<template>

    <div>
        <md-table  md-height="800px" class="my-table" v-model="entries" v-if="count" md-card md-fixed-header>
            <md-table-toolbar>
                <md-badge  class="md-square md-primary" :md-content="count">
                    <h3 class="md-title"  style="flex: 1" ><font-awesome-icon icon="users" />   Groups  </h3>
                </md-badge>
                <md-button :href="resource_url" title="JSON" target="_blank" class="md-icon-button md-raised">
                    <font-awesome-icon icon="code"/>
                </md-button>

            </md-table-toolbar>

            <md-table-row slot="md-table-row" slot-scope="{item}">

                <md-table-cell md-label="Info">
                    <div class="my-info">
                        <div class="item">
                            <md-list class="md-double-line">

                                <div class="md-list-item-text">
                                    <span>{{ item.name }}</span>
                                    <span>Name</span>
                                </div>
                                <div class="md-list-item-text">
                                    <span>{{ item.count }}</span>
                                    <span>Count</span>
                                </div>
                                <div class="md-list-item-text">
                                    <span>{{ item.study_name }}</span>
                                    <span>Study</span>
                                </div>

                            </md-list>
                        </div>

                        <div class="item">

                            <md-badge title="Individuals" v-if="item.individuals" class="md-square md-primary " :md-content="item.individuals.length">
                                <md-button @click="showDialog = true" class="md-icon-button md-raised">
                                    <font-awesome-icon icon="user" />
                                </md-button>
                            </md-badge>


                                <md-dialog :md-active.sync="showDialog">
                                    <md-dialog-content>
                                        <Individuals :api="api"/>
                                    </md-dialog-content>
                                </md-dialog>

                            <md-button :href="api + '/groups_read/'+ item.pk +'/?format=json'" title="JSON" target="_blank" class="md-icon-button md-raised" >
                                <font-awesome-icon icon="code"/>
                            </md-button>
                        </div>
                    </div>
                </md-table-cell>

                <md-table-cell md-label="Characteristica">
                    <div class="my-cell">
                        <CharacteristicaChip  class="item" v-for="(c, index1) in item.characteristica_all_final" :key="index1" :api="api" :id="id_from_url(c)"/>
                    </div>
                </md-table-cell>
            </md-table-row>
        </md-table>
        <v-paginator :resource_url="resource_url"  @update="updateResource" config=""></v-paginator>
    </div>


</template>
<script>

    import VuePaginator from '@/components/VPaginator';
    import Individuals from './Individuals';
    import CharacteristicaChip from './CharacteristicaChip';

    import {id_from_url} from "./utils";

    export default {
    name: 'Groups',
    components: {
        VPaginator: VuePaginator,
        CharacteristicaChip: CharacteristicaChip,
        Individuals:Individuals,

    },
    props: {
        api: String
    },
    methods:{
        updateResource(data){
            this.entries = data.data;
            this.count = data.count
        },
        id_from_url(url){
            return id_from_url(url);
        }
    },
    data() {
        return {
            entries: [],
            count: null,
            resource_url: this.api + '/groups_read/?format=json',
            showDialog: false,
        }
        }
}
</script>
<style>
    .my-table{
        table-layout: fixed;
        width: inherit;

    }
    .my-cell {
        display:block;
        white-space: nowrap;
        height: 105px;
        padding-left: 2px;

    }
    .my-info {
        padding-left: 2px;
        white-space: nowrap;
        width: 156px;
        display: flex;
        justify-content: space-between;




    }
    .item {
        display: inline-block;

    }
    .md-dialog {
        max-width: 768px;
    }


</style>