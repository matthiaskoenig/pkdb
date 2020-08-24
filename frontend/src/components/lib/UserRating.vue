<template>
    <span id="user-rating">
         <v-chip flat
                 color="white"
         >
          <user-avatar :user="user"/>
             <v-rating v-if="user.rating != null"
                       v-model="user.rating"
                       :title="'Curation score: '+ user.rating"
                       dense
                       half-increments
                       value
                       x-small
                       readonly
             />
        </v-chip>
    </span>
</template>

<script>
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