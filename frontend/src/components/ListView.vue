<template>
    <span id="list-view"></span>
        <get-paginated-data :resource_url="resource_url">
            <template slot="data">

                    <slot name="listview" v-bind:data="data"></slot>

            </template>

            <!--<span slot-scope="data"></span>-->
                <!--{{ data }}-->
                <!--<slot v-bind:data="data"></slot>-->
        </get-paginated-data>
    </template>
</template>

<script>
    import GetPaginatedData from './api/GetPaginatedData';
    export default {
        name: 'ListView',
        components: {
            GetPaginatedData: GetPaginatedData,
        },
        props: {
            resource_url: {
                type: String,
                required: true
            }
        }
    }
</script>
<style>
</style>