<template>
    <span id="user-rating">
         <v-chip>
          <user-avatar :user="user"/>
             <v-rating v-if="user.rating != null" v-model="user.rating" :title="'Curation score: '+ user.rating" dense half-increments value small readonly/>
        </v-chip>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "UserRating",
        props: {

            user: {
                type: Object,
                required: true,
            },
        }
    }
</script>

<style scoped>
</style>